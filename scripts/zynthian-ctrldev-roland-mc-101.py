#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver for Roland MC-101
#
# Native Zynthian Vangelis ctrldev driver providing bidirectional sync between
# the Roland MC-101 and ZynSeq:
#   1. Transport Sync (Start 0xFA / Continue 0xFB / Stop 0xFC)
#   2. Bidirectional Scene <-> Phrase Row Launch (Control Ch 16 Program Change)
#   3. Bidirectional Clip <-> Per-Chain Sequence Launch (Track Ch 1-4 PC 0-15)
# Includes strict idempotency and state-tracking guards to prevent MIDI loops.
# ******************************************************************************

import logging
from time import monotonic

from zyncoder.zyncore import lib_zyncore
from zyngine.ctrldev.zynthian_ctrldev_base import zynthian_ctrldev_base
from zyngine.zynthian_signal_manager import zynsigman
from zynlibs.zynseq import zynseq


class zynthian_ctrldev_roland_mc_101(zynthian_ctrldev_base):

    dev_ids = ["MC-101 IN 1", "MC-101"]
    driver_name = "Roland MC-101"
    driver_description = "Roland MC-101 Bidirectional Transport, Scene & Clip Launcher Sync"

    # Keep MC-101 MIDI channels routed to chains so notes and CCs (e.g. CC 80-83)
    # can still play and modulate Zynthian synths when desired.
    unroute_from_chains = False
    autoload_flag = True

    # Default MC-101 MIDI channel assignments (0-indexed)
    TRACK_CHANNELS = (0, 1, 2, 3)   # MIDI Channels 1-4 (Tracks 1-4)
    CONTROL_CHANNEL = 15            # MIDI Channel 16 (Scene Control Channel)
    MAX_MC101_CLIPS = 16            # 16 Clips per track on MC-101 (PC 0..15)
    MAX_MC101_SCENES = 128          # 128 Scenes on MC-101 (PC 0..127)

    def __init__(self, state_manager, idev_in, idev_out=None):
        super().__init__(state_manager, idev_in, idev_out)
        self._last_transport_ts = 0.0
        self._last_phrase_launch_ts = 0.0

        # Loop-prevention state trackers:
        # Track which Scene (Phrase row) and per-channel Clip are already active/queued
        # on the MC-101 so we never echo an incoming MC-101 PC back out, nor double-send
        # when ZynSeq transitions from SEQ_STARTING (orange) -> SEQ_PLAYING (green).
        self._mc101_active_scene = None
        self._mc101_active_clips = {}

        # Timestamp guards to ignore echoed PCs after outgoing/incoming transitions
        self._rx_scene_guard_ts = 0.0
        self._tx_scene_guard_ts = 0.0
        self._rx_clip_guard_ts = {}
        self._tx_clip_guard_ts = {}

    def init(self):
        super().init()
        zynsigman.register_queued(
            zynsigman.S_STEPSEQ, zynsigman.SS_SEQ_PLAY_STATE, self.on_seq_play_state
        )
        logging.info(
            f"[Roland MC-101] ctrldev initialized on idev_in={self.idev}, idev_out={self.idev_out}"
        )

    def end(self):
        zynsigman.unregister(
            zynsigman.S_STEPSEQ, zynsigman.SS_SEQ_PLAY_STATE, self.on_seq_play_state
        )
        logging.info("[Roland MC-101] ctrldev terminated")
        super().end()

    # --------------------------------------------------------------------------
    # Outgoing MIDI Helper (Zynthian -> MC-101)
    # --------------------------------------------------------------------------

    def _send_program_change(self, midi_chan, pgm):
        """Send a 2-byte MIDI Program Change message to the MC-101."""
        if not self.idev_out or self.idev_out <= 0:
            return
        status = 0xC0 | (midi_chan & 0x0F)
        msg = bytes([status, pgm & 0x7F])
        lib_zyncore.dev_send_midi_event(self.idev_out, msg, len(msg))

    # --------------------------------------------------------------------------
    # Incoming Actions (MC-101 -> Zynthian)
    # --------------------------------------------------------------------------

    def _ensure_phrase_exists(self, phrase_idx):
        """Ensure the requested phrase row exists in the active ZynSeq scene."""
        if phrase_idx < 0:
            return 0
        if phrase_idx >= self.zynseq.phrases:
            return max(0, self.zynseq.phrases - 1)
        return phrase_idx

    def _get_seq_state(self, scene, phrase, chan):
        """Return the low-byte play state (SEQ_STOPPED, SEQ_PLAYING, SEQ_STARTING, etc.)."""
        return self.zynseq.libseq.getSequenceState(scene, phrase, chan) & 0xFF

    def _is_seq_enabled(self, scene, phrase, chan):
        """Return True if the sequence slot is non-empty and has repeat > 0."""
        if self.zynseq.libseq.isEmpty(scene, phrase, chan):
            return False
        state_word = self.zynseq.libseq.getSequenceState(scene, phrase, chan)
        repeat = (state_word >> 24) & 0xFF
        return repeat > 0

    def _start_active_phrase(self):
        """Start the currently selected Phrase row and all its child sequences immediately."""
        scene = self.zynseq.scene
        phrase = self._ensure_phrase_exists(self.zynseq.phrase)
        now = monotonic()
        self._last_phrase_launch_ts = now
        self._mc101_active_scene = phrase
        self._rx_scene_guard_ts = now

        logging.info(f"[Roland MC-101] Starting ZynSeq scene={scene}, phrase={phrase}")

        # 1. Reset transport to STOPPED first so transportStart triggers a fresh Bar 1 Beat 1 (bSync=true)
        self.zynseq.transport_stop("mc101")
        self.zynseq.transport_stop("zynseq")

        # 2. Set the Phrase Launcher to SEQ_STARTING then SEQ_PLAYING so all active child sequences
        #    start immediately on Bar 1 Beat 1 even if external MIDI clock already ticked once.
        self.zynseq.libseq.setPlayState(
            scene, phrase, zynseq.PHRASE_CHANNEL, zynseq.SEQ_STARTING
        )
        self.zynseq.libseq.setPlayState(
            scene, phrase, zynseq.PHRASE_CHANNEL, zynseq.SEQ_PLAYING
        )
        for chan in range(zynseq.PHRASE_CHANNEL):
            if self._is_seq_enabled(scene, phrase, chan):
                if chan in self.TRACK_CHANNELS:
                    self._mc101_active_clips[chan] = phrase
                    self._rx_clip_guard_ts[chan] = now
                self.zynseq.libseq.setPlayState(
                    scene, phrase, chan, zynseq.SEQ_PLAYING
                )

    def _stop_all_phrases_and_sequences(self):
        """Immediately stop all playing Phrase rows, child sequences, and transport."""
        scene = self.zynseq.scene
        logging.info(f"[Roland MC-101] Stopping ZynSeq scene={scene} phrases and transport")
        self._mc101_active_scene = None
        self._mc101_active_clips.clear()

        for phrase in range(self.zynseq.phrases):
            for chan in range(zynseq.PHRASE_CHANNEL + 1):
                state = self._get_seq_state(scene, phrase, chan)
                if state != zynseq.SEQ_STOPPED:
                    self.zynseq.libseq.setPlayState(
                        scene, phrase, chan, zynseq.SEQ_STOPPED
                    )
        self.zynseq.transport_stop("mc101")
        self.zynseq.transport_stop("zynseq")

    def _launch_phrase_row(self, phrase_idx):
        """Select and launch a full ZynSeq Phrase row (triggered by MC-101 Scene PC)."""
        if phrase_idx < 0 or phrase_idx >= self.zynseq.phrases:
            logging.warning(
                f"[Roland MC-101] Scene PC {phrase_idx} out of range (phrases={self.zynseq.phrases})"
            )
            return

        now = monotonic()
        # Loop guard: ignore if Zynthian just sent this Scene PC to the MC-101
        if phrase_idx == self._mc101_active_scene and (now - self._tx_scene_guard_ts) < 2.0:
            return

        scene = self.zynseq.scene
        cur_state = self._get_seq_state(scene, phrase_idx, zynseq.PHRASE_CHANNEL)

        # Record MC-101 scene state before changing ZynSeq so on_seq_play_state won't echo it back
        self._mc101_active_scene = phrase_idx
        self._rx_scene_guard_ts = now
        self._last_phrase_launch_ts = now
        for chan in self.TRACK_CHANNELS:
            if self._is_seq_enabled(scene, phrase_idx, chan):
                self._mc101_active_clips[chan] = phrase_idx
                self._rx_clip_guard_ts[chan] = now

        # Idempotency guard: if this Phrase row is already queued (SEQ_STARTING) or playing (SEQ_PLAYING), do not re-toggle
        if cur_state in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
            return

        self.zynseq.select_phrase(phrase_idx)
        logging.info(f"[Roland MC-101] RX Scene Launch -> ZynSeq scene={scene}, phrase={phrase_idx}")

        # Queue the target Phrase row on the bar boundary (SEQ_STARTING = orange play icon)
        self.zynseq.libseq.setPlayState(
            scene, phrase_idx, zynseq.PHRASE_CHANNEL, zynseq.SEQ_STARTING
        )

        # Ensure any playing sequence on a chain where the new Phrase row is empty stops cleanly at the bar boundary
        for chan in range(zynseq.PHRASE_CHANNEL):
            if not self._is_seq_enabled(scene, phrase_idx, chan):
                for other_phrase in range(self.zynseq.phrases):
                    if other_phrase != phrase_idx:
                        st = self._get_seq_state(scene, other_phrase, chan)
                        if st in (zynseq.SEQ_PLAYING, zynseq.SEQ_STARTING):
                            self.zynseq.libseq.setPlayState(
                                scene, other_phrase, chan, zynseq.SEQ_STOPPING
                            )

    def _launch_chain_clip(self, midi_chan, phrase_idx):
        """Launch a specific sequence/clip on a single MIDI channel (triggered by MC-101 Clip PC)."""
        if phrase_idx < 0 or phrase_idx >= self.zynseq.phrases:
            logging.warning(
                f"[Roland MC-101] Clip PC {phrase_idx} on Ch {midi_chan + 1} out of range (phrases={self.zynseq.phrases})"
            )
            return

        now = monotonic()
        # Loop guard: ignore if Zynthian just sent this Clip PC to the MC-101
        if (
            self._mc101_active_clips.get(midi_chan) == phrase_idx
            and (now - self._tx_clip_guard_ts.get(midi_chan, 0.0)) < 2.0
        ):
            return

        scene = self.zynseq.scene

        # Record MC-101 clip state before changing ZynSeq so on_seq_play_state won't echo it back
        self._mc101_active_clips[midi_chan] = phrase_idx
        self._rx_clip_guard_ts[midi_chan] = now

        # 1. Trigger MIDI sequence column (0..15) quantized to bar sync (SEQ_STARTING)
        if self._is_seq_enabled(scene, phrase_idx, midi_chan):
            cur_state = self._get_seq_state(scene, phrase_idx, midi_chan)
            if cur_state not in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
                logging.info(
                    f"[Roland MC-101] RX Clip Launch -> ZynSeq scene={scene}, phrase={phrase_idx}, midi_chan={midi_chan + 1}"
                )
                self.zynseq.libseq.setPlayState(
                    scene, phrase_idx, midi_chan, zynseq.SEQ_STARTING
                )

        # 2. Also trigger Clippy audio launcher column (16..31) if a Clippy chain uses this MIDI channel
        clippy_chan = midi_chan + 16
        if clippy_chan < zynseq.PHRASE_CHANNEL:
            try:
                chain_ids = self.chain_manager.get_chain_ids_by_midi_chan(midi_chan)
                for cid in chain_ids:
                    chain = self.chain_manager.chains.get(cid)
                    if chain and chain.get_clippy_processor():
                        cur_cstate = self._get_seq_state(scene, phrase_idx, clippy_chan)
                        if cur_cstate not in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
                            self.zynseq.libseq.setPlayState(
                                scene, phrase_idx, clippy_chan, zynseq.SEQ_STARTING
                            )
                        break
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Outgoing ZynSeq State Listener (Zynthian UI -> MC-101)
    # --------------------------------------------------------------------------

    def on_seq_play_state(self, phrase, chan):
        """Called when a Phrase row or Sequence pad changes play state in ZynSeq."""
        if not self.idev_out or self.idev_out <= 0:
            return

        scene = self.zynseq.scene
        if phrase < 0 or phrase >= self.zynseq.phrases:
            return

        state = self._get_seq_state(scene, phrase, chan)
        now = monotonic()

        # A. Phrase Row Launcher (chan == 32) -> Send Scene Program Change on Control Channel (Ch 16)
        if chan == zynseq.PHRASE_CHANNEL:
            if state in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
                self._last_phrase_launch_ts = now
                # Do not send if this phrase is already the active/queued MC-101 scene
                # (prevents echoing MC-101 Scene PCs and prevents double-sending on STARTING -> PLAYING)
                if phrase == self._mc101_active_scene:
                    return
                if (now - self._rx_scene_guard_ts) < 0.25:
                    return
                if phrase < self.MAX_MC101_SCENES:
                    self._mc101_active_scene = phrase
                    self._tx_scene_guard_ts = now
                    # Update tracked clips for all enabled child sequences in this row so their
                    # simultaneous child state signals are not mistaken for individual clip launches
                    for trk_chan in self.TRACK_CHANNELS:
                        if self._is_seq_enabled(scene, phrase, trk_chan):
                            self._mc101_active_clips[trk_chan] = phrase
                            self._tx_clip_guard_ts[trk_chan] = now
                    logging.info(
                        f"[Roland MC-101] TX Scene Launch -> MC-101 Ch {self.CONTROL_CHANNEL + 1} PC {phrase}"
                    )
                    self._send_program_change(self.CONTROL_CHANNEL, phrase)
            elif state == zynseq.SEQ_STOPPED:
                if self._mc101_active_scene == phrase:
                    self._mc101_active_scene = None
            return

        # B. Individual Sequence / Clippy Pad -> Send Clip Program Change on Track Channel (Ch 1-4)
        midi_chan = chan if chan < 16 else (chan - 16)
        if midi_chan not in self.TRACK_CHANNELS or phrase >= self.MAX_MC101_CLIPS:
            return

        if state in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
            # 1. Suppress if this sequence state change is part of a full Phrase row launch
            #    (Note: in zynseq.cpp getStateChange(), child channels 0..31 are emitted before
            #    PHRASE_CHANNEL 32, so during a Phrase launch phrase_state is either SEQ_STARTING
            #    or SEQ_PLAYING with _mc101_active_scene != phrase).
            phrase_state = self._get_seq_state(scene, phrase, zynseq.PHRASE_CHANNEL)
            if phrase_state == zynseq.SEQ_STARTING or (
                phrase_state == zynseq.SEQ_PLAYING and self._mc101_active_scene != phrase
            ):
                return
            if (now - self._last_phrase_launch_ts) < 0.25:
                return

            # 2. Loop & transition guard: do not send if this clip is already active/queued on the MC-101
            if self._mc101_active_clips.get(midi_chan) == phrase:
                return
            if (now - self._rx_clip_guard_ts.get(midi_chan, 0.0)) < 0.25:
                return

            self._mc101_active_clips[midi_chan] = phrase
            self._tx_clip_guard_ts[midi_chan] = now
            logging.info(
                f"[Roland MC-101] TX Clip Launch -> MC-101 Ch {midi_chan + 1} PC {phrase}"
            )
            self._send_program_change(midi_chan, phrase)

        elif state == zynseq.SEQ_STOPPED:
            if self._mc101_active_clips.get(midi_chan) == phrase:
                self._mc101_active_clips[midi_chan] = None

    # --------------------------------------------------------------------------
    # Real-Time MIDI Event Handler (MC-101 -> Zynthian)
    # --------------------------------------------------------------------------

    def midi_event(self, ev):
        """Intercept MIDI Transport (0xFA/0xFB/0xFC) and Scene/Clip Program Changes."""
        if not ev:
            return False

        evhead = ev[0]

        # 1. System Real-Time Transport Messages (Channel-less: 0xFA, 0xFB, 0xFC)
        if evhead in (zynseq.MIDI_START, zynseq.MIDI_CONTINUE):
            now = monotonic()
            if now - self._last_transport_ts > 0.05:
                self._last_transport_ts = now
                self._start_active_phrase()
            return True

        if evhead == zynseq.MIDI_STOP:
            now = monotonic()
            if now - self._last_transport_ts > 0.05:
                self._last_transport_ts = now
                self._stop_all_phrases_and_sequences()
            return True

        evtype = (evhead >> 4) & 0x0F
        evchan = evhead & 0x0F

        # 2. Program Change (0xC0..0xCF): Scene Launch (Control Ch) or Clip Launch (Track Ch 1-4)
        if evtype == 0x0C and len(ev) >= 2:
            pgm = ev[1] & 0x7F

            # A. Control Channel (Default Ch 16) -> Launch Full Phrase Row
            if evchan == self.CONTROL_CHANNEL:
                self._launch_phrase_row(pgm)
                return True

            # B. Track Channels 1-4 (Ch 1-4) -> Launch Clip on Matching Zynthian MIDI Channel
            if evchan in self.TRACK_CHANNELS:
                self._launch_chain_clip(evchan, pgm)
                return True

        # Return False for all other events (Notes, CCs, Pitch Bend) so they pass through to chains
        return False
