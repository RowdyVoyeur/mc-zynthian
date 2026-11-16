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
#
# Transport FROM Zynthian TO the MC-101 is carried by zynseq's own clock output
# ("Send MIDI Clock" enabled), which emits 0xFA when zynseq transport starts and
# 0xFC when it stops. Outgoing Program Changes use dev_send_program_change()
# (which writes a 3-byte record to ZynMidiRouter's ringbuffer, as required by
# populate_midi_event_from_rb() in zynmidirouter.c).
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

    # zynseq C API: transportStop(255) clears all transport clients
    TRANSPORT_ALL_CLIENTS = 255

    # Guard windows (seconds)
    RX_ECHO_GUARD = 1.5             # Ignore TX echoes of PCs received from the MC-101
    TX_ECHO_GUARD = 2.0             # Ignore RX echoes of PCs sent to the MC-101

    def __init__(self, state_manager, idev_in, idev_out=None):
        super().__init__(state_manager, idev_in, idev_out)
        self._last_rx_transport_ts = 0.0
        self._zyn_was_playing = False
        self._suppress_tx_until = 0.0

        # Directional loop-prevention guards: (phrase_idx, timestamp)
        self._rx_scene_guard = (None, 0.0)
        self._tx_scene_guard = (None, 0.0)
        self._rx_clip_guard = {}
        self._tx_clip_guard = {}

    def init(self):
        super().init()
        self._zyn_was_playing = self._zynseq_is_running()
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
    # ZynSeq helpers
    # --------------------------------------------------------------------------

    def _get_seq_state(self, scene, phrase, chan):
        """Return the low-byte play state (SEQ_STOPPED, SEQ_PLAYING, SEQ_STARTING, etc.)."""
        return self.zynseq.libseq.getSequenceState(scene, phrase, chan) & 0xFF

    def _is_seq_enabled(self, scene, phrase, chan):
        """Return True if the sequence slot is non-empty and has repeat > 0."""
        if self.zynseq.libseq.isEmpty(scene, phrase, chan):
            return False
        state_word = self.zynseq.libseq.getSequenceState(scene, phrase, chan)
        return ((state_word >> 24) & 0xFF) > 0

    def _running_slots(self):
        """List (phrase, chan) slots in the current scene that are PLAYING or STARTING."""
        scene = self.zynseq.scene
        slots = []
        for phrase in range(self.zynseq.phrases):
            for chan in range(zynseq.PHRASE_CHANNEL + 1):
                if self._get_seq_state(scene, phrase, chan) in (zynseq.SEQ_PLAYING, zynseq.SEQ_STARTING):
                    slots.append((phrase, chan))
        return slots

    def _zynseq_is_running(self):
        """True if any sequence or phrase launcher is playing or queued in ZynSeq."""
        if self.zynseq.libseq.getPlayingSequences() > 0:
            return True
        return bool(self._running_slots())

    def _ensure_phrase_exists(self, phrase_idx):
        if phrase_idx < 0:
            return 0
        if phrase_idx >= self.zynseq.phrases:
            return max(0, self.zynseq.phrases - 1)
        return phrase_idx

    # --------------------------------------------------------------------------
    # Outgoing MIDI helpers (Zynthian -> MC-101)
    # --------------------------------------------------------------------------

    def _has_midi_out(self):
        """Return True if a valid ZynMidiRouter output slot (0-indexed) is attached."""
        return self.idev_out is not None and self.idev_out >= 0

    def _send_program_change(self, midi_chan, pgm):
        """Send a Program Change using dev_send_program_change (3-byte ringbuffer record)."""
        if not self._has_midi_out():
            return
        lib_zyncore.dev_send_program_change(self.idev_out, midi_chan & 0x0F, pgm & 0x7F)

    # --------------------------------------------------------------------------
    # Incoming actions (MC-101 -> Zynthian)
    # --------------------------------------------------------------------------

    def _start_active_phrase(self):
        """Start the currently selected Phrase row and all its child sequences immediately."""
        scene = self.zynseq.scene
        phrase = self._ensure_phrase_exists(self.zynseq.phrase)
        now = monotonic()
        self._zyn_was_playing = True
        self._suppress_tx_until = now + self.RX_ECHO_GUARD
        self._rx_scene_guard = (phrase, now)
        for chan in self.TRACK_CHANNELS:
            self._rx_clip_guard[chan] = (phrase, now)

        logging.warning(f"[Roland MC-101] RX Start -> ZynSeq scene={scene}, phrase={phrase}")

        self.zynseq.libseq.transportStop(self.TRANSPORT_ALL_CLIENTS)
        self.zynseq.libseq.setPlayState(scene, phrase, zynseq.PHRASE_CHANNEL, zynseq.SEQ_STARTING)
        self.zynseq.libseq.setPlayState(scene, phrase, zynseq.PHRASE_CHANNEL, zynseq.SEQ_PLAYING)
        for chan in range(zynseq.PHRASE_CHANNEL):
            st = self._get_seq_state(scene, phrase, chan)
            if self._is_seq_enabled(scene, phrase, chan) or st == zynseq.SEQ_STARTING:
                self.zynseq.libseq.setPlayState(scene, phrase, chan, zynseq.SEQ_PLAYING)

    def _stop_all_phrases_and_sequences(self):
        """Immediately stop all playing Phrase rows, child sequences, and transport."""
        scene = self.zynseq.scene
        logging.warning(f"[Roland MC-101] RX Stop -> ZynSeq scene={scene}")
        self._zyn_was_playing = False
        self._suppress_tx_until = monotonic() + 0.5
        for phrase, chan in self._running_slots():
            self.zynseq.libseq.setPlayState(scene, phrase, chan, zynseq.SEQ_STOPPED)
        self.zynseq.libseq.transportStop(self.TRANSPORT_ALL_CLIENTS)

    def _launch_phrase_row(self, phrase_idx):
        """Select and launch a full ZynSeq Phrase row (triggered by MC-101 Scene PC)."""
        if phrase_idx < 0 or phrase_idx >= self.zynseq.phrases:
            logging.warning(
                f"[Roland MC-101] Scene PC {phrase_idx} out of range (phrases={self.zynseq.phrases})"
            )
            return

        now = monotonic()
        tx_phrase, tx_ts = self._tx_scene_guard
        if tx_phrase == phrase_idx and (now - tx_ts) < self.TX_ECHO_GUARD:
            return

        scene = self.zynseq.scene
        self._rx_scene_guard = (phrase_idx, now)
        for chan in self.TRACK_CHANNELS:
            self._rx_clip_guard[chan] = (phrase_idx, now)

        if self._get_seq_state(scene, phrase_idx, zynseq.PHRASE_CHANNEL) in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
            return

        self.zynseq.select_phrase(phrase_idx)

        # MC-101 stopped: only select the row; [PLAY] on the MC-101 will start it (RX Start)
        if not self._zynseq_is_running():
            logging.warning(f"[Roland MC-101] RX Scene Select (stopped) -> ZynSeq phrase={phrase_idx}")
            return

        logging.warning(f"[Roland MC-101] RX Scene Launch -> ZynSeq scene={scene}, phrase={phrase_idx}")
        self.zynseq.libseq.setPlayState(scene, phrase_idx, zynseq.PHRASE_CHANNEL, zynseq.SEQ_STARTING)

        # Stop chains whose slot in the new row is empty at the bar boundary
        for chan in range(zynseq.PHRASE_CHANNEL):
            if not self._is_seq_enabled(scene, phrase_idx, chan):
                for other_phrase in range(self.zynseq.phrases):
                    if other_phrase != phrase_idx:
                        if self._get_seq_state(scene, other_phrase, chan) in (zynseq.SEQ_PLAYING, zynseq.SEQ_STARTING):
                            self.zynseq.libseq.setPlayState(scene, other_phrase, chan, zynseq.SEQ_STOPPING)

    def _launch_chain_clip(self, midi_chan, phrase_idx):
        """Launch a specific sequence/clip on a single MIDI channel (triggered by MC-101 Clip PC)."""
        if phrase_idx < 0 or phrase_idx >= self.zynseq.phrases:
            logging.warning(
                f"[Roland MC-101] Clip PC {phrase_idx} on Ch {midi_chan + 1} out of range (phrases={self.zynseq.phrases})"
            )
            return

        now = monotonic()
        tx_clip, tx_ts = self._tx_clip_guard.get(midi_chan, (None, 0.0))
        if tx_clip == phrase_idx and (now - tx_ts) < self.TX_ECHO_GUARD:
            return

        scene = self.zynseq.scene
        self._rx_clip_guard[midi_chan] = (phrase_idx, now)

        # MC-101 stopped: don't start Zynthian on its own (it would desync the MC-101)
        if not self._zynseq_is_running():
            return

        if self._is_seq_enabled(scene, phrase_idx, midi_chan):
            if self._get_seq_state(scene, phrase_idx, midi_chan) not in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
                logging.warning(
                    f"[Roland MC-101] RX Clip Launch -> ZynSeq scene={scene}, phrase={phrase_idx}, midi_chan={midi_chan + 1}"
                )
                self.zynseq.libseq.setPlayState(scene, phrase_idx, midi_chan, zynseq.SEQ_STARTING)

        clippy_chan = midi_chan + 16
        if clippy_chan < zynseq.PHRASE_CHANNEL:
            try:
                for cid in self.chain_manager.get_chain_ids_by_midi_chan(midi_chan):
                    chain = self.chain_manager.chains.get(cid)
                    if chain and chain.get_clippy_processor():
                        if self._get_seq_state(scene, phrase_idx, clippy_chan) not in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
                            self.zynseq.libseq.setPlayState(scene, phrase_idx, clippy_chan, zynseq.SEQ_STARTING)
                        break
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Outgoing ZynSeq state listener (Zynthian UI -> MC-101)
    # --------------------------------------------------------------------------

    def on_seq_play_state(self, phrase, chan):
        """Translate Zynthian UI launches into MC-101 Program Changes.

        - While playing: send PC only when a pad enters SEQ_STARTING (orange), so both
          devices switch on the same bar boundary. A Phrase row click sends ONLY a Scene PC;
          an individual pad click sends ONLY a Clip PC.
        - On cold start from stop: send the Scene/Clip PC immediately without restarting ZynSeq.
        """
        if not self._has_midi_out():
            return
        now = monotonic()
        if now < self._suppress_tx_until:
            return

        scene = self.zynseq.scene
        if phrase < 0 or phrase >= self.zynseq.phrases:
            return

        state = self._get_seq_state(scene, phrase, chan)

        # Track stop (zynseq's clock output sends 0xFC to the MC-101 by itself)
        if state == zynseq.SEQ_STOPPED:
            if not self._zynseq_is_running():
                self._zyn_was_playing = False
            return

        if state not in (zynseq.SEQ_STARTING, zynseq.SEQ_PLAYING):
            return

        cold_start = not self._zyn_was_playing

        # A. Phrase row launcher -> Scene PC (Ch 16)
        if chan == zynseq.PHRASE_CHANNEL:
            if state == zynseq.SEQ_PLAYING and not cold_start:
                return  # STARTING -> PLAYING transition at bar end: already sent
            rx_phrase, rx_ts = self._rx_scene_guard
            if rx_phrase == phrase and (now - rx_ts) < self.RX_ECHO_GUARD:
                return
            if phrase >= self.MAX_MC101_SCENES:
                return
            self._zyn_was_playing = True
            self._tx_scene_guard = (phrase, now)
            for trk_chan in self.TRACK_CHANNELS:
                self._tx_clip_guard[trk_chan] = (phrase, now)
            logging.warning(
                f"[Roland MC-101] TX Scene Launch -> MC-101 Ch {self.CONTROL_CHANNEL + 1} PC {phrase}"
            )
            self._send_program_change(self.CONTROL_CHANNEL, phrase)
            return

        # B. Individual sequence / Clippy pad -> Clip PC (Ch 1-4)
        midi_chan = chan if chan < 16 else (chan - 16)
        if midi_chan not in self.TRACK_CHANNELS or phrase >= self.MAX_MC101_CLIPS:
            return

        phrase_state = self._get_seq_state(scene, phrase, zynseq.PHRASE_CHANNEL)
        if phrase_state == zynseq.SEQ_STARTING or (cold_start and phrase_state == zynseq.SEQ_PLAYING):
            return  # Part of a Phrase row launch -> Scene PC handles it
        if state == zynseq.SEQ_PLAYING and not cold_start:
            return  # STARTING -> PLAYING transition at bar end: already sent

        rx_clip, rx_ts = self._rx_clip_guard.get(midi_chan, (None, 0.0))
        if rx_clip == phrase and (now - rx_ts) < self.RX_ECHO_GUARD:
            return
        tx_clip, tx_ts = self._tx_clip_guard.get(midi_chan, (None, 0.0))
        if tx_clip == phrase and (now - tx_ts) < 0.25:
            return

        self._zyn_was_playing = True
        self._tx_clip_guard[midi_chan] = (phrase, now)
        logging.warning(
            f"[Roland MC-101] TX Clip Launch -> MC-101 Ch {midi_chan + 1} PC {phrase}"
        )
        self._send_program_change(midi_chan, phrase)

    # --------------------------------------------------------------------------
    # Real-time MIDI event handler (MC-101 -> Zynthian)
    # --------------------------------------------------------------------------

    def midi_event(self, ev):
        """Intercept MIDI Transport (0xFA/0xFB/0xFC) and Scene/Clip Program Changes."""
        if not ev:
            return False

        evhead = ev[0]
        now = monotonic()

        # 1. Transport. The MC-101 retransmits Start/Stop it receives from zynseq's clock
        #    output, so echoes must be filtered:
        #    - Start while ZynSeq is already running = echo of Zynthian's own start
        if evhead in (zynseq.MIDI_START, zynseq.MIDI_CONTINUE):
            if self._zynseq_is_running():
                return True
            if now - self._last_rx_transport_ts > 0.05:
                self._last_rx_transport_ts = now
                self._start_active_phrase()
            return True

        if evhead == zynseq.MIDI_STOP:
            if now - self._last_rx_transport_ts > 0.05:
                self._last_rx_transport_ts = now
                self._stop_all_phrases_and_sequences()
            return True

        evtype = (evhead >> 4) & 0x0F
        evchan = evhead & 0x0F

        # 2. Program Change: Scene (Control Ch) or Clip (Track Ch 1-4)
        if evtype == 0x0C and len(ev) >= 2:
            pgm = ev[1] & 0x7F
            if evchan == self.CONTROL_CHANNEL:
                self._launch_phrase_row(pgm)
                return True
            if evchan in self.TRACK_CHANNELS:
                self._launch_chain_clip(evchan, pgm)
                return True

        # Notes, CCs, Pitch Bend pass through to chains
        return False
