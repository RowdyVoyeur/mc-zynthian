# `mc-zynthian` Project Manifest: Core Architecture & Roadmap

**Project Vision**
To engineer a self-contained, ultra-low-latency electronic music performance hub. This project builds a fully autonomous Zynthian-based ecosystem, bridging a Roland MC-101, Ableton Push 1, Korg nanoKONTROL, and a repurposed Teensy 4.1 into a unified routing and deep-editing powerhouse driven by a Raspberry Pi 4 and Blokas Pisound.

---

## Stage 1: Standalone DIY Zynthian
**Hardware:** Raspberry Pi 4 + Pisound + Macro Keyboard + Touchscreen
**Goal:** Establish a rock-solid, ultra-low-latency foundation that can be fully operated without external MIDI controllers. Refer to the [Pisound Guide (`docs/pisound-guide.md`)](docs/pisound-guide.md) for full installation, low-latency configuration, and The Button operation.

- [ ] **OS Deployment:** Install and configure the Zynthian OS on the Raspberry Pi 4.
- [ ] **Pisound Audio I/O:** Configure Pisound as the primary audio interface (see [`docs/pisound-guide.md`](docs/pisound-guide.md)). Achieve ultra-low latency audio matching or exceeding previous setup benchmarks.
- [ ] **Pisound MIDI I/O:** Ensure hardware MIDI IN and OUT ports work flawlessly.
- [ ] **Display Calibration:** Ensure the touchscreen works reliably to interact with the Zynthian UI.
- [ ] **Macro Keyboard Navigation:** Map the macro keyboard to be the primary navigation tool (see [`docs/macrokeyboard-guide.md`](docs/macrokeyboard-guide.md)). (Requirement: The RPi must be fully operable autonomously via this keyboard, with the touchscreen acting only as an optional assist).
- [ ] **Pisound Button Mapping:** Enable the physical button on the Pisound to execute context-specific tasks (via `pisound-btn` and CUIA, see [`docs/pisound-guide.md`](docs/pisound-guide.md)), such as changing audio routing on the fly.

## Stage 2: Enhanced Ecosystem
**Hardware:** Stage 1 + Roland MC-101 + Korg nanoKONTROL
**Goal:** Integrate external synthesizers and baseline physical control, achieving seamless audio/MIDI sync and deep hardware editing.

- [ ] **nanoKONTROL Integration:** Configure the Korg nanoKONTROL to drive Zynthian's transport controls, navigation, and primary system parameters (see [`docs/nanokontrol-guide.md`](docs/nanokontrol-guide.md)).
- [ ] **MC-101 USB MIDI Sync:** Ensure flawless MIDI IN/OUT via USB with the MC-101 (see [`docs/mc101-guide.md`](docs/mc101-guide.md)), allowing seamless clock synchronization.
- [ ] **MC-101 USB Audio Transport:** Connect both master and per-track audio (IN and OUT) from the MC-101 to the Pi via USB at very low latency.
- [ ] **Dynamic Audio Routing:** Enable on-the-fly audio routing (preferably via the Zynthian UI) to patch Pisound inputs to the MC-101, Zynthian master to MC-101 inputs, MC-101 tracks to Zynthian effects, etc.
- [ ] **Zen-Core Editing Bridge:** Create a way to edit MC-101 Zen-Core parameters directly from the Zynthian UI, powered by a Python SysEx script.
- [ ] **Drum Track Deep Editing:** Expand the editing bridge to manipulate MC-101 drum track parameters to the furthest extent the hardware allows.

## Stage 3: Full-Fledged Ecosystem
**Hardware:** Stage 2 + Ableton Push 1 + Teensy 4.1
**Goal:** Introduce advanced "eyes-off-the-Pi" operation and integrate a custom hardware synth voice.

- [ ] **Push 1 Deep Integration:** Configure the Ableton Push 1 to control Zynthian deeply (via `pushy.py`, see [`docs/push-guide.md`](docs/push-guide.md)), ensuring the entire ecosystem can be navigated and played almost without looking at the Pi's screen.
- [ ] **Teensy 4.1 Synthesizer:** Flash the Teensy 4.1 with a dedicated synth firmware.
- [ ] **Teensy Integration:** Connect and configure the Teensy via USB so it can be controlled by Zynthian's sequencers and routed through its audio matrix.