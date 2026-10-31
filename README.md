# `mc-zynthian` Project Manifest: Core Architecture & Roadmap

**Project Vision**
To engineer a self-contained, ultra-low-latency electronic music performance hub. This project builds a fully autonomous Zynthian-based ecosystem, bridging a Roland MC-101, Ableton Push 1, Korg nanoKONTROL, and a repurposed Teensy 4.1 into a unified routing and deep-editing powerhouse driven by a Raspberry Pi 4 and Blokas Pisound.

---

## Stage 1: Standalone DIY Zynthian
**Hardware:** Raspberry Pi 4 + Pisound + Macro Keyboard + Touchscreen (see [Hardware Specs & Enclosure Manual (`docs/rpi-specs.md`)](docs/rpi-specs.md) and 3D assembly model [`assets/case-assembly.stl`](assets/case-assembly.stl))
**Goal:** Establish a rock-solid, ultra-low-latency foundation that can be fully operated without external MIDI controllers. Refer to the [Zynthian Vangelis Guide (`docs/zynthian-guide.md`)](docs/zynthian-guide.md) for OS architecture, Webconf setup, and low-latency tuning, and the [Pisound Guide (`docs/pisound-guide.md`)](docs/pisound-guide.md) for soundcard configuration and The Button operation.

- [ ] **OS Deployment:** Install and configure ZynthianOS Vangelis on the Raspberry Pi 4 (see [`docs/zynthian-guide.md`](docs/zynthian-guide.md) and [`docs/rpi-specs.md`](docs/rpi-specs.md)).
- [ ] **Pisound Audio I/O:** Configure Pisound as the primary audio interface (see [`docs/pisound-guide.md`](docs/pisound-guide.md)). Achieve ultra-low latency audio matching or exceeding previous setup benchmarks.
- [ ] **Pisound MIDI I/O:** Ensure hardware MIDI IN and OUT ports work flawlessly.
- [ ] **Display Calibration:** Ensure the touchscreen works reliably to interact with the Zynthian UI (see native timings in [`docs/rpi-specs.md`](docs/rpi-specs.md)).
- [ ] **Macro Keyboard Navigation:** Map the macro keyboard to be the primary navigation tool (see [`docs/macrokeyboard-guide.md`](docs/macrokeyboard-guide.md)). (Requirement: The RPi must be fully operable autonomously via this keyboard, with the touchscreen acting only as an optional assist).
- [ ] **Pisound Button Mapping:** Enable the physical button on the Pisound to execute context-specific tasks (via native Webconf switch mapping or `pisound-btn` daemon and CUIA, see [`docs/pisound-guide.md`](docs/pisound-guide.md)), such as changing audio routing on the fly.

## Stage 2: Enhanced Ecosystem
**Hardware:** Stage 1 + Roland MC-101 + Korg nanoKONTROL
**Goal:** Integrate external synthesizers and baseline physical control, achieving seamless audio/MIDI sync and deep hardware editing. Refer to the [Software Integration & Plugin Blueprint (`docs/software-integration.md`)](docs/software-integration.md) for the `mc101-ctrl.lv2` plugin, `mcee-audio.sh` multi-track audio daemon, and `scripts/kontroller.py` driver.

- [ ] **nanoKONTROL Integration:** Configure the Korg nanoKONTROL to drive Zynthian's transport controls, navigation, and primary system parameters (see [`docs/nanokontrol-guide.md`](docs/nanokontrol-guide.md) and [`docs/software-integration.md`](docs/software-integration.md)).
- [ ] **MC-101 USB MIDI Sync:** Ensure flawless MIDI IN/OUT via USB with the MC-101 (see [`docs/mc101-guide.md`](docs/mc101-guide.md)), allowing seamless clock synchronization.
- [ ] **MC-101 USB Audio Transport:** Connect both master and per-track audio (IN and OUT) from the MC-101 to the Pi via USB at very low latency (via `scripts/mcee-audio.sh`, see [`docs/software-integration.md`](docs/software-integration.md)).
- [ ] **Dynamic Audio Routing:** Enable on-the-fly audio routing (preferably via the Zynthian UI) to patch Pisound inputs to the MC-101, Zynthian master to MC-101 inputs, MC-101 tracks to Zynthian effects, etc.
- [ ] **Zen-Core Editing Bridge:** Create a native LV2 plugin (`mc101-ctrl.lv2`) to edit MC-101 Zen-Core parameters directly from the Zynthian UI (see [`docs/software-integration.md`](docs/software-integration.md) and [`docs/mc101-sysex.md`](docs/mc101-sysex.md)).
- [ ] **Drum Track Deep Editing:** Expand the editing bridge to manipulate MC-101 drum track parameters to the furthest extent the hardware allows (see [`docs/software-integration.md`](docs/software-integration.md)).

## Stage 3: Full-Fledged Ecosystem
**Hardware:** Stage 2 + Ableton Push 1 + Teensy 4.1
**Goal:** Introduce advanced "eyes-off-the-Pi" operation and integrate a custom hardware synth voice.

- [ ] **Push 1 Deep Integration:** Configure the Ableton Push 1 to control Zynthian deeply (via `pushy.py`, see [`docs/push-guide.md`](docs/push-guide.md) and [`docs/software-integration.md`](docs/software-integration.md)), ensuring the entire ecosystem can be navigated and played almost without looking at the Pi's screen.
- [ ] **Teensy 4.1 Synthesizer / Co-Processor:** Select and flash the Teensy 4.1 firmware (e.g., Headless Mini-Teensy-Synth or Euclidean MIDI Co-Processor; see [`docs/teensy-guide.md`](docs/teensy-guide.md)).
- [ ] **Teensy Integration:** Connect and configure the Teensy via USB so it can be controlled by Zynthian's sequencers and routed through its audio matrix (see [`docs/teensy-guide.md`](docs/teensy-guide.md)).