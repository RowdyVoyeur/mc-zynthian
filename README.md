# `mc-zynthian` Project Manifest: Core Architecture & Roadmap

**Project Vision**
To engineer a self-contained, ultra-low-latency electronic music performance hub. This project builds a fully autonomous Zynthian-based ecosystem, bridging a Roland MC-101, Ableton Push 1, Korg nanoKONTROL, and a repurposed Teensy 4.1 into a unified routing and deep-editing powerhouse driven by a Raspberry Pi 4 and Blokas Pisound.

---

## Project Roadmap & Task List

### Stage 1: Standalone DIY Zynthian
**Hardware:** Raspberry Pi 4 + Pisound + Macro Keyboard + Touchscreen (see [Hardware Specs & Enclosure Manual (`docs/rpi-specs.md`)](docs/rpi-specs.md) and 3D assembly model [`assets/case-assembly.stl`](assets/case-assembly.stl))
**Goal:** Establish a rock-solid, ultra-low-latency foundation that can be fully operated without external MIDI controllers. Refer to the [Zynthian Vangelis Guide (`docs/zynthian-guide.md`)](docs/zynthian-guide.md) for OS architecture, Webconf setup, and low-latency tuning, and the [Pisound Guide (`docs/pisound-guide.md`)](docs/pisound-guide.md) for soundcard configuration and The Button operation.

- [x] **OS Deployment:** Install and configure ZynthianOS Vangelis on the Raspberry Pi 4 (see [`docs/zynthian-guide.md`](docs/zynthian-guide.md) and [`docs/rpi-specs.md`](docs/rpi-specs.md)).
- [x] **Display Calibration:** Ensure the touchscreen works reliably to interact with the Zynthian UI (see native timings in [`docs/rpi-specs.md`](docs/rpi-specs.md)).
- [ ] **Pisound Audio I/O:** Configure Pisound as the primary audio interface (see [`docs/pisound-guide.md`](docs/pisound-guide.md)). Achieve ultra-low latency audio matching or exceeding previous setup benchmarks. *(Audio Out verified; Audio In pending test)*
- [ ] **Pisound MIDI I/O:** Ensure hardware MIDI IN and OUT ports work flawlessly.
- [ ] **Macro Keyboard Navigation:** Map the macro keyboard to be the primary navigation tool (see [`docs/macrokeyboard-guide.md`](docs/macrokeyboard-guide.md)). (Requirement: The RPi must be fully operable autonomously via this keyboard, with the touchscreen acting only as an optional assist). *(Hardware detected & working; keybindings pending)*
- [ ] **Pisound Button Mapping:** Enable the physical button on the Pisound to execute context-specific tasks (via native Webconf switch mapping or `pisound-btn` daemon and CUIA, see [`docs/pisound-guide.md`](docs/pisound-guide.md)), such as changing audio routing on the fly.

### Stage 2: Enhanced Ecosystem
**Hardware:** Stage 1 + Roland MC-101 + Korg nanoKONTROL
**Goal:** Integrate external synthesizers and baseline physical control, achieving seamless audio/MIDI sync and deep hardware editing. Refer to the [Software Integration & Plugin Blueprint (`docs/software-integration.md`)](docs/software-integration.md) for the `mc101-ctrl.lv2` plugin, `mcee-audio.sh` multi-track audio daemon, and `scripts/kontroller.py` driver.

- [ ] **nanoKONTROL Integration:** Configure the Korg nanoKONTROL to drive Zynthian's transport controls, navigation, and primary system parameters (see [`docs/nanokontrol-guide.md`](docs/nanokontrol-guide.md) and [`docs/software-integration.md`](docs/software-integration.md)).
- [ ] **MC-101 USB MIDI Sync:** Ensure flawless MIDI IN/OUT via USB with the MC-101 (see [`docs/mc101-guide.md`](docs/mc101-guide.md)), allowing seamless clock synchronization.
- [ ] **MC-101 USB Audio Transport:** Connect both master and per-track audio (IN and OUT) from the MC-101 to the Pi via USB at very low latency (via `scripts/mcee-audio.sh`, see [`docs/software-integration.md`](docs/software-integration.md)).
- [ ] **Dynamic Audio Routing:** Enable on-the-fly audio routing (preferably via the Zynthian UI) to patch Pisound inputs to the MC-101, Zynthian master to MC-101 inputs, MC-101 tracks to Zynthian effects, etc.
- [ ] **Zen-Core Editing Bridge:** Create a native LV2 plugin (`mc101-ctrl.lv2`) to edit MC-101 Zen-Core parameters directly from the Zynthian UI (see [`docs/software-integration.md`](docs/software-integration.md) and [`docs/mc101-sysex.md`](docs/mc101-sysex.md)).
- [ ] **Drum Track Deep Editing:** Expand the editing bridge to manipulate MC-101 drum track parameters to the furthest extent the hardware allows (see [`docs/software-integration.md`](docs/software-integration.md)).

### Stage 3: Full-Fledged Ecosystem
**Hardware:** Stage 2 + Ableton Push 1 + Teensy 4.1
**Goal:** Introduce advanced "eyes-off-the-Pi" operation and integrate a custom hardware synth voice.

- [ ] **Push 1 Deep Integration:** Configure the Ableton Push 1 to control Zynthian deeply (via `pushy.py`, see [`docs/push-guide.md`](docs/push-guide.md) and [`docs/software-integration.md`](docs/software-integration.md)), ensuring the entire ecosystem can be navigated and played almost without looking at the Pi's screen.
- [ ] **Teensy 4.1 Synthesizer / Co-Processor:** Select and flash the Teensy 4.1 firmware (e.g., Headless Mini-Teensy-Synth or Euclidean MIDI Co-Processor; see [`docs/teensy-guide.md`](docs/teensy-guide.md)).
- [ ] **Teensy Integration:** Connect and configure the Teensy via USB so it can be controlled by Zynthian's sequencers and routed through its audio matrix (see [`docs/teensy-guide.md`](docs/teensy-guide.md)).

---

## Step-by-Step Configuration Guide

### Stage 1: Initial Setup

#### Step 1: Flashing the OS Image
1. Downloaded `zynthianos-last-stable.img.xz` from `https://os.zynthian.org/`
2. Opened Raspberry Pi Imager and used custom OS `zynthianos-last-stable.img.xz`
3. Selected the SD card as storage device
4. Selected write
5. After 20 minutes it was flashed onto the SD card

#### Step 2: First Boot & Initial Hardware Setup
1. **Boot Screen Observations & Initial Error:**
   - On first boot, the screen displayed:
     - `IP: Audio/MIDI (1) to (4)`
     - `IP: 192.168.x.x Audio/MIDI (5) to (57)` (increasing counter)
     - An `Error` message was presented on the loading screen (soundcard unconfigured on fresh image).
     - Eventually the IP changed to `10.42.0.xxx`, and the error remained.
2. **Accessing Webconf:**
   - Connected an Ethernet cable.
   - Opened a web browser and navigated to `http://10.42.0.xxx`.
   - Logged in with password: `opensynth`.
3. **Audio Configuration:**
   - Navigated to the **Hardware** menu $\to$ **Audio**.
   - Soundcard: **Pisound**.
   - Soundcard Device: **Pisound**.
   - Sample Rate: **48000**.
   - Buffer Size: **64**.
   - Number of Buffers: **2**.
   - Clicked **Save**.
   - The errors on the display disappeared, and Webconf displayed: *"Zynthian needs to reboot to apply your changes!"*
4. **Kit & Display Configuration (before rebooting):**
   - Navigated to **Hardware** $\to$ **Kit** and selected **Custom**.
   - Navigated to **Hardware** $\to$ **Display**, selected **Waveshare 5 HDMI+USB**, and set Rotation to **None**.
   - Clicked **Save** and rebooted.
5. **Post-Reboot Verification:**
   - System booted cleanly without errors.
   - **Audio Out:** Verified working.
   - **Touchscreen:** Verified working.
   - **Macro Keyboard:** Verified detected and working.

#### Step 3: Macro Keyboard Configuration (SayoDevice 2x6F RGB)
1. **Linux Mint WebHID Permissions:**
   - Plugged keyboard into Linux Mint PC.
   - Configured udev rule to allow browser access to raw HID devices:
     ```bash
     echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666"' | sudo tee /etc/udev/rules.d/99-sayodevice.rules
     sudo udevadm control --reload-rules && sudo udevadm trigger
     ```
   - Reconnected USB cable to apply permissions.
2. **Firmware Upgrade & Web Portal Transition:**
   - Connected via `https://old.sayodevice.com/device` and upgraded device firmware.
   - Successfully transitioned to the modern configurator at `https://app.sayodevice.com/`.
3. **Key Matrix Programmed into EEPROM:**
   - **Layer 0 (Default):**
     - Row 1: Key 1: `none` | Key 2: `Up` | Key 3: `none` | Key 4: `Fn` (Press & Hold for Layer 1) | Key 5: `A` | Key 6: `B`
     - Row 2: Key 7: `Left` | Key 8: `Down` | Key 9: `Right` | Key 10: `none` | Key 11: `C` | Key 12: `D`
   - **Layer 1 (Fn Held):**
     - Row 1: Key 1: `none` | Key 2: `I` | Key 3: `none` | Key 4: `none` | Key 5: `E` | Key 6: `F`
     - Row 2: Key 7: `K` | Key 8: `J` | Key 9: `L` | Key 10: `none` | Key 11: `G` | Key 12: `H`

#### Step 4: Zynthian UI Keybindings Configuration (Layer 0 & V5 Hardware Functions)
Configured in Zynthian Webconf under **Interface** $\rightarrow$ **UI Keybindings** to enable autonomous "no-touchscreen" operation:

1. **Design Principle:**
   - **Layer 0 (Navigation, Selection & Knobs):**
     - D-Pad Left/Right: Focus parameter / select active knob / change column.
     - D-Pad Up/Down: Adjust focused knob value (increments/decrements) / scroll list / adjust fader.
     - Key 5 (`A`): Primary Confirm / Enter (`SELECT`).
     - Key 6 (`B`): Back / Cancel / Exit (`BACK`).
     - Key 11 (`C`): Instant View Toggle between Mixer/Launcher and Synth Control View (`SWITCH_VIEW`).
     - Key 12 (`D`): Master Transport Play / Stop toggle (`TOGGLE_PLAY`).
   - **Layer 1 (V5 Hardware Button Functions - `Fn` Held):**
     - D-Pad Up/Down (`I` / `J`): Fast scroll / Coarse knob adjustment in steps of 10 (`PAGE_UP` / `PAGE_DOWN`).
     - D-Pad Left/Right (`K` / `L`): Instant sound preset / subsnapshot switching (`PREV_SNAPSHOT` / `NEXT_SNAPSHOT`).
     - Key 5 (`E`): Context Options Menu / Track Options / MIDI Learn (`BOLD_SELECT`).
     - Key 6 (`F`): V5 Emergency Panic / Silence all hanging notes (`ALL_NOTES_OFF`).
     - Key 11 (`G`): Dedicated Snapshot Browser Screen (`SCREEN_SNAPSHOT`).
     - Key 12 (`H`): Dedicated Master Stereo Audio Recording (`TOGGLE_AUDIO_RECORD`).

2. **Webconf UI Keybindings Assignment Table:**

| Key | Layer | Hardware Cluster | Target CUIA Action | Function |
|---|---|---|---|---|
| **`Up`** | Layer 0 | D-Pad Top | `ARROW_UP` | Turn focused knob up / scroll list up |
| **`Down`** | Layer 0 | D-Pad Bottom | `ARROW_DOWN` | Turn focused knob down / scroll list down |
| **`Left`** | Layer 0 | D-Pad Left | `ARROW_LEFT` | Select previous knob / move column left |
| **`Right`** | Layer 0 | D-Pad Right | `ARROW_RIGHT` | Select next knob / move column right |
| **`a`** | Layer 0 | Action A (Row 1, Col 5) | `SELECT` | Confirm / Enter / Open submenu |
| **`b`** | Layer 0 | Action B (Row 1, Col 6) | `BACK` | Back / Cancel / Exit |
| **`c`** | Layer 0 | Action C (Row 2, Col 5) | `SWITCH_VIEW` | Toggle Mixer/Launcher $\leftrightarrow$ Synth Control view |
| **`d`** | Layer 0 | Action D (Row 2, Col 6) | `TOGGLE_PLAY` | Global transport Play / Stop toggle |
| **`i`** | Layer 1 | D-Pad Top (`Fn` held) | `PAGE_UP` | Coarse knob jump (+10) / fast scroll up |
| **`j`** | Layer 1 | D-Pad Bottom (`Fn` held) | `PAGE_DOWN` | Coarse knob jump (-10) / fast scroll down |
| **`k`** | Layer 1 | D-Pad Left (`Fn` held) | `PREV_SNAPSHOT` | Load previous sound preset |
| **`l`** | Layer 1 | D-Pad Right (`Fn` held) | `NEXT_SNAPSHOT` | Load next sound preset |
| **`e`** | Layer 1 | Action A (`Fn` held) | `BOLD_SELECT` | Context options menu (Bold click) |
| **`f`** | Layer 1 | Action B (`Fn` held) | `ALL_NOTES_OFF` | V5 Panic: Cut all hung notes |
| **`g`** | Layer 1 | Action C (`Fn` held) | `SCREEN_SNAPSHOT` | Open Snapshots & Presets view |
| **`h`** | Layer 1 | Action D (`Fn` held) | `TOGGLE_AUDIO_RECORD` | Start / Stop master audio recording |

#### Next Steps:
- Apply keybindings in Webconf and test live navigation and knob tweaking.
- Verify Pisound Audio In, MIDI In, and MIDI Out.
