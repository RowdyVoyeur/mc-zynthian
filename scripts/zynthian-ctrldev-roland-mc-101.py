#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver for Roland MC-101
#
# Native Zynthian Vangelis ctrldev driver bridging Roland MC-101 transport
# (Start/Continue/Stop), Scene changes (Control Channel Program Change ->
# ZynSeq Phrase Launcher row), and per-track Clip changes (Track Channel 1-4
# Program Change -> ZynSeq per-channel Sequence/Clippy launcher).
# ******************************************************************************

import logging
from time import monotonic

from zyngine.ctrldev.zynthian_ctrldev_base import zynthian_ctrldev_base
from zynlibs.zynseq import zynseq


class zynthian_ctrldev_roland_mc_101(zynthian_ctrldev_base):

    dev_ids = ["MC-101 IN 1", "MC-101"]
    driver_name = "Roland MC-101"
    driver_description = "Roland MC-101 Transport, Scene & Clip Launcher Sync"

    # Keep MC-101 MIDI channels routed to chains so notes and CCs (e.g. CC 80-83)
    # can still play and modulate Zynthian synths when desired.
    unroute_from_chains = False
    autoload_flag = True

    # Default MC-101 MIDI channel assignments (0-indexed)
    TRACK_CHANNELS = (0, 1, 2, 3)   # MIDI Channels 1-4 (Tracks 1-4)
    CONTROL_CHANNEL = 15            # MIDI Channel 16 (Scene Control Channel)

    def __init__(self, state_manager, idev_in, idev_out=None):
        super().__init__(state_manager, idev_in, idev_out)
        self._last_transport_ts = 0.0

    def init(self):
        super().init()
        logging.info(f"[Roland MC-101] ctrldev initialized on idev_in={self.idev}, idev_out={self.idev_out}")

    def end(self):
        logging.info("[Roland MC-101] ctrldev terminated")
        super().end()

    # --------------------------------------------------------------------------
    # Helper Actions: Phrase, Clip, and Transport Control
    # --------------------------------------------------------------------------

    def _ensure_phrase_exists(self, phrase_idx):
        """Ensure the requested phrase row exists in the active ZynSeq scene."""
        if phrase_idx < 0:
            return 0
        if phrase_idx >= self.zynseq.phrases:
            return max(0, self.zynseq.phrases - 1)
        return phrase_idx

    def _start_active_phrase(self):
        """Start the currently selected Phrase row and all its child sequences immediately."""
        scene = self.zynseq.scene
        phrase = self._ensure_phrase_exists(self.zynseq.phrase)
        logging.info(f"[Roland MC-101] Starting ZynSeq scene={scene}, phrase={phrase}")

        # 1. Reset transport to STOPPED first so transportStart triggers a fresh Bar 1 Beat 1 (bSync=true)
        #    on the very next audio cycle.
        self.zynseq.transport_stop("mc101")
        self.zynseq.transport_stop("zynseq")

        # 2. Set the Phrase Launcher to SEQ_STARTING (which also marks all active child sequences
        #    as STARTING and calls transportStart("zynseq") -> g_nTransportState = STARTING -> bSync = true).
        self.zynseq.libseq.setPlayState(
            scene, phrase, zynseq.PHRASE_CHANNEL, zynseq.SEQ_STARTING
        )

        # 3. Also explicitly set any enabled child sequences in this phrase to SEQ_PLAYING
        #    in case external MIDI clock already ticked past the initial bSync frame before Python woke up.
        self.zynseq.libseq.setPlayState(
            scene, phrase, zynseq.PHRASE_CHANNEL, zynseq.SEQ_PLAYING
        )
        for chan in range(zynseq.PHRASE_CHANNEL):
            if not self.zynseq.libseq.isEmpty(scene, phrase, chan):
                state_word = self.zynseq.libseq.getSequenceState(scene, phrase, chan)
                repeat = (state_word >> 24) & 0xFF
                if repeat > 0:
                    self.zynseq.libseq.setPlayState(
                        scene, phrase, chan, zynseq.SEQ_PLAYING
                    )

    def _stop_all_phrases_and_sequences(self):
        """Immediately stop all playing Phrase rows, child sequences, and transport."""
        scene = self.zynseq.scene
        logging.info(f"[Roland MC-101] Stopping ZynSeq scene={scene} phrases and transport")
        for phrase in range(self.zynseq.phrases):
            for chan in range(zynseq.PHRASE_CHANNEL + 1):
                state = self.zynseq.libseq.getSequenceState(scene, phrase, chan) & 0xFF
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
        scene = self.zynseq.scene
        self.zynseq.select_phrase(phrase_idx)
        logging.info(f"[Roland MC-101] Scene Launch -> ZynSeq scene={scene}, phrase={phrase_idx}")
        # Use SEQ_STARTING so the phrase and all its child sequences launch quantized on the bar boundary
        self.zynseq.libseq.setPlayState(
            scene, phrase_idx, zynseq.PHRASE_CHANNEL, zynseq.SEQ_STARTING
        )

    def _launch_chain_clip(self, midi_chan, phrase_idx):
        """Launch a specific sequence/clip on a single MIDI channel (triggered by MC-101 Clip PC)."""
        if phrase_idx < 0 or phrase_idx >= self.zynseq.phrases:
            logging.warning(
                f"[Roland MC-101] Clip PC {phrase_idx} on Ch {midi_chan + 1} out of range (phrases={self.zynseq.phrases})"
            )
            return
        scene = self.zynseq.scene
        logging.info(
            f"[Roland MC-101] Clip Launch -> ZynSeq scene={scene}, phrase={phrase_idx}, midi_chan={midi_chan + 1}"
        )
        # Trigger MIDI sequence column (0..15) quantized to bar sync (SEQ_STARTING)
        if not self.zynseq.libseq.isEmpty(scene, phrase_idx, midi_chan):
            self.zynseq.libseq.setPlayState(
                scene, phrase_idx, midi_chan, zynseq.SEQ_STARTING
            )
        # Also trigger Clippy audio launcher column (16..31) if a Clippy chain uses this MIDI channel
        clippy_chan = midi_chan + 16
        if clippy_chan < zynseq.PHRASE_CHANNEL:
            try:
                chain_ids = self.chain_manager.get_chain_ids_by_midi_chan(midi_chan)
                for cid in chain_ids:
                    chain = self.chain_manager.chains.get(cid)
                    if chain and chain.get_clippy_processor():
                        self.zynseq.libseq.setPlayState(
                            scene, phrase_idx, clippy_chan, zynseq.SEQ_STARTING
                        )
                        break
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Real-Time MIDI Event Handler
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
