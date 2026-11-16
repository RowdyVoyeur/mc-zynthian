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
        self._zyn_was_playing = False

        # Directional loop-prevention guards:
        #   _rx_scene_guard: (phrase_idx, timestamp) set when MC-101 -> Zynthian triggers a Scene
        #   _tx_scene_guard: (phrase_idx, timestamp) set when Zynthian -> MC-101 triggers a Scene
        #   _rx_clip_guard[chan]: (phrase_idx, timestamp) set when MC-101 -> Zynthian triggers a Clip
        #   _tx_clip_guard[chan]: (phrase_idx, timestamp) set when Zynthian -> MC-101 triggers a Clip
        self._rx_scene_guard = (None, 0.0)
        self._tx_scene_guard = (None, 0.0)
        self._rx_clip_guard = {}
        self._tx_clip_guard = {}

    def init(self):
        super().init()
        self._zyn_was_playing = bool(self.zynseq.libseq.getPlayingSequences() > 0)
        zynsigman.register_queued(
            zynsigman.S_STEPSEQ, zynsigman.SS_SEQ_PLAY_STATE, self.on_seq_play_state
        )
        logging.warning(
            f"[Roland MC-101] ctrldev initialized on idev_in={self.idev}, idev_out={self.idev_out}"
        )

    def end(self):
        zynsigman.unregister(
            zynsigman.S_STEPSEQ, zynsigman.SS_SEQ_PLAY_STATE, self.on_seq_play_state
        )
        logging.warning("[Roland MC-101] ctrldev terminated")
        super().end()

    # --------------------------------------------------------------------------
    # Outgoing MIDI Helpers (Zynthian -> MC-101)
    # --------------------------------------------------------------------------

    def _has_midi_out(self):
        """Return True if a valid ZynMidiRouter output slot (0-indexed) is attached."""
        return self.idev_out is not None and self.idev_out >= 0

    def _send_midi_bytes(self, raw_bytes):
        """Send raw MIDI bytes to the MC-101 output port."""
        if not self._has_midi_out():
            return
        msg = bytes(raw_bytes)
        lib_zyncore.dev_send_midi_event(self.idev_out, msg, len(msg))

    def _send_program_change(self, midi_chan, pgm):
        """Send a 2-byte MIDI Program Change message to the MC-101."""
        status = 0xC0 | (midi_chan & 0x0F)
        self._send_midi_bytes([status, pgm & 0x7F])

    def _send_pc_and_start_if_stopped(self, midi_chan, pgm):
        """Send a Scene/Clip Program Change to the MC-101; if starting from stop, align Bar 1 Beat 1."""
        if not self._zyn_was_playing:
            self._zyn_was_playing = True
            self._last_transport_ts = monotonic()
            self._send_midi_bytes([zynseq.MIDI_STOP])
            self._send_program_change(midi_chan, pgm)
            self._send_midi_bytes([zynseq.MIDI_START])
        else:
            self._send_program_change(midi_chan, pgm)

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
        self._zyn_was_playing = True
        self._rx_scene_guard = (phrase, now)

        logging.warning(f"[Roland MC-101] RX Start -> ZynSeq scene={scene}, phrase={phrase}")

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
                    self._rx_clip_guard[chan] = (phrase, now)
                self.zynseq.libseq.setPlayState(
                    scene, phrase, chan, zynseq.SEQ_PLAYING
                )

    def _stop_all_phrases_and_sequences(self):
        """Immediately stop all playing Phrase rows, child sequences, and transport."""
        scene = self.zynseq.scene
        logging.warning(f"[Roland MC-101] RX Stop -> ZynSeq scene={scene}")
        self._zyn_was_playing = False

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
        tx_phrase, tx_ts = self._tx_scene_guard
        if tx_phrase == phrase_idx and (now - tx_ts) < 2.0:
            return

        scene = self.zynseq.scene
        cur_state = self._get_seq_state(scene, phrase_idx, zynseq.PHRASE_CHANNEL)

        # Record RX guard before changing ZynSeq so on_seq_play_state won't echo it back
        self._zyn_was_playing = True
        self._rx_scene_guard = (phrase_idx, now)
        for chan in self.TRACK_CHANNELS:
            self._rx_clip_guard[chan] = (phrase_idx, now)

        # Idempotency guard: if this Phrase row is already queued (SEQ_STARTING) or playing (SEQ_PLAYING), do not re-toggle
        if cur_state in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
            return

        self.zynseq.select_phrase(phrase_idx)
        logging.warning(f"[Roland MC-101] RX Scene Launch -> ZynSeq scene={scene}, phrase={phrase_idx}")

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
        tx_clip, tx_ts = self._tx_clip_guard.get(midi_chan, (None, 0.0))
        if tx_clip == phrase_idx and (now - tx_ts) < 2.0:
            return

        scene = self.zynseq.scene

        # Record RX guard before changing ZynSeq so on_seq_play_state won't echo it back
        self._zyn_was_playing = True
        self._rx_clip_guard[midi_chan] = (phrase_idx, now)

        # 1. Trigger MIDI sequence column (0..15) quantized to bar sync (SEQ_STARTING)
        if self._is_seq_enabled(scene, phrase_idx, midi_chan):
            cur_state = self._get_seq_state(scene, phrase_idx, midi_chan)
            if cur_state not in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
                logging.warning(
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
        """Called when a Phrase row or Sequence pad changes play state in ZynSeq.

        CRITICAL DESIGN RULE:
        - When Zynthian is ALREADY PLAYING (_zyn_was_playing == True):
          Clicking any Phrase row or Clip pad in Zynthian's UI puts that pad into
          SEQ_STARTING (orange play icon) immediately upon click, and transitions
          it to SEQ_PLAYING (green play icon) at the end of the bar.
          Therefore, while playing we MUST ONLY transmit Program Change on
          state == SEQ_STARTING (never on SEQ_PLAYING!).
          Furthermore:
            * Clicking a Phrase row (chan == 32) sets PHRASE_CHANNEL (32) AND all its
              children (0..31) to SEQ_STARTING. Child channels see
              phrase_state == SEQ_STARTING and are completely ignored, so a Phrase row
              click ONLY ever sends a Scene PC (Ch 16).
            * Clicking an individual Clip pad (chan 0..3) sets ONLY that clip to
              SEQ_STARTING while PHRASE_CHANNEL (32) is NOT SEQ_STARTING, so a Clip
              pad click ONLY ever sends a Clip PC (Ch 1-4) immediately upon click!
        - When Zynthian is STOPPED (_zyn_was_playing == False):
          Clicking a pad starts transport on tick 0 so the pad jumps directly to
          SEQ_PLAYING before Python's GUI timer polls getStateChange(). In that case:
            * If a Phrase row was clicked, PHRASE_CHANNEL (32) is SEQ_PLAYING.
            * If an individual Clip pad was clicked, PHRASE_CHANNEL (32) is SEQ_CHILD_PLAYING.
        """
        if not self._has_midi_out():
            return

        scene = self.zynseq.scene
        if phrase < 0 or phrase >= self.zynseq.phrases:
            return

        state = self._get_seq_state(scene, phrase, chan)
        now = monotonic()

        # Check if all sequences in ZynSeq have stopped
        if state == zynseq.SEQ_STOPPED and self.zynseq.libseq.getPlayingSequences() == 0:
            if self._zyn_was_playing and (now - self._last_transport_ts) > 0.1:
                self._zyn_was_playing = False
                self._last_transport_ts = now
                logging.warning("[Roland MC-101] TX Stop -> MC-101 (all ZynSeq sequences stopped)")
                self._send_midi_bytes([zynseq.MIDI_STOP])
            return

        # A. Phrase Row Launcher (chan == 32) -> Send Scene Program Change on Control Channel (Ch 16)
        if chan == zynseq.PHRASE_CHANNEL:
            is_queued_launch = (state == zynseq.SEQ_STARTING)
            is_cold_start = (state == zynseq.SEQ_PLAYING and not self._zyn_was_playing)
            if is_queued_launch or is_cold_start:
                rx_phrase, rx_ts = self._rx_scene_guard
                if rx_phrase == phrase and (now - rx_ts) < 0.5:
                    return
                tx_phrase, tx_ts = self._tx_scene_guard
                if tx_phrase == phrase and (now - tx_ts) < 0.25:
                    return
                if phrase < self.MAX_MC101_SCENES:
                    self._tx_scene_guard = (phrase, now)
                    logging.warning(
                        f"[Roland MC-101] TX Scene Launch -> MC-101 Ch {self.CONTROL_CHANNEL + 1} PC {phrase}"
                    )
                    self._send_pc_and_start_if_stopped(self.CONTROL_CHANNEL, phrase)
            return

        # B. Individual Sequence / Clippy Pad -> Send Clip Program Change on Track Channel (Ch 1-4)
        midi_chan = chan if chan < 16 else (chan - 16)
        if midi_chan not in self.TRACK_CHANNELS or phrase >= self.MAX_MC101_CLIPS:
            return

        phrase_state = self._get_seq_state(scene, phrase, zynseq.PHRASE_CHANNEL)

        # Trigger ONLY when an individual clip is queued (SEQ_STARTING while parent Phrase row
        # is NOT launching) OR cold-started from stop (SEQ_PLAYING while parent Phrase row is SEQ_CHILD_PLAYING)
        is_clip_queued = (
            state == zynseq.SEQ_STARTING and phrase_state != zynseq.SEQ_STARTING
        )
        is_clip_cold_start = (
            state == zynseq.SEQ_PLAYING
            and not self._zyn_was_playing
            and phrase_state == zynseq.SEQ_CHILD_PLAYING
        )

        if is_clip_queued or is_clip_cold_start:
            rx_clip, rx_ts = self._rx_clip_guard.get(midi_chan, (None, 0.0))
            if rx_clip == phrase and (now - rx_ts) < 0.5:
                return
            tx_clip, tx_ts = self._tx_clip_guard.get(midi_chan, (None, 0.0))
            if tx_clip == phrase and (now - tx_ts) < 0.25:
                return

            self._tx_clip_guard[midi_chan] = (phrase, now)
            logging.warning(
                f"[Roland MC-101] TX Clip Launch -> MC-101 Ch {midi_chan + 1} PC {phrase}"
            )
            self._send_pc_and_start_if_stopped(midi_chan, phrase)

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
