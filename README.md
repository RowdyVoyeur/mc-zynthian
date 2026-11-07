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
- [ ] **Pisound Audio I/O:** Configure Pisound as the primary audio interface (see [`docs/pisound-guide.md`](docs/pisound-guide.md)). Achieve ultra-low latency audio matching or exceeding previous setup benchmarks. *(Audio Out verified at 48kHz, buffer size 128, 5.3ms latency, zero XRUNs; Audio In pending test)*
- [ ] **Pisound MIDI I/O:** Ensure hardware MIDI IN and OUT ports work flawlessly.
- [ ] **Macro Keyboard Navigation:** Map the macro keyboard to be the primary navigation tool (see [`docs/sanyodevice-guide.md`](docs/sanyodevice-guide.md)). (Requirement: The RPi must be fully operable autonomously via this keyboard, with the touchscreen acting only as an optional assist). *(Hardware detected & working; keybindings pending)*
- [x] **Pisound Button Mapping:** Enable the physical button on the Pisound natively without extra packages (Short press: Admin Menu `SCREEN_ADMIN`, Long press: Power Menu `POWER`, see [`docs/pisound-guide.md`](docs/pisound-guide.md)). *(Verified working and persistent across reboots)*

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
   - Buffer Size: **128** *(initially tested at 64, but increased to 128 to eliminate frequent XRUNs in UI Log; achieves rock-solid 5.3ms latency)*.
   - Number of Buffers: **2**.
   - Clicked **Save**.
   - The errors on the display disappeared, and Webconf displayed: *"Zynthian needs to reboot to apply your changes!"*
4. **Kit & Display Configuration (before rebooting):**
   - Navigated to **Hardware** $\to$ **Kit** and selected **Custom**.
   - Navigated to **Hardware** $\to$ **Display**, selected **Waveshare 5 HDMI+USB**, and set Rotation to **None**.
   - Clicked **Save** and rebooted.
5. **Post-Reboot Verification:**
   - System booted cleanly without errors.
   - **Audio Out:** Verified working with **5.3ms latency** and zero XRUNs at buffer size 128.
   - **Touchscreen:** Verified working.
   - **Macro Keyboard:** Verified detected and working.

#### Step 3: Macro Keyboard Configuration (SayoDevice 2x6F RGB — 5-Layer Matrix)
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
   - Transitioned to the modern configurator at `https://app.sayodevice.com/`.
3. **5-Layer Architecture Programmed into EEPROM:**
   - **Key 4 Cyclical Layer Switcher:** Key 4 (Row 1, Col 4) advances cyclically through 5 layers:
     $$\text{Layer 0} \longrightarrow \text{Layer 1} \longrightarrow \text{Layer 2} \longrightarrow \text{Layer 3} \longrightarrow \text{Layer 4} \longrightarrow \text{Layer 0}$$
   - **Persistent Keys Across All 5 Layers:**
     - Row 1: Key 1: `none` | Key 2: `Up` | Key 3: `none` | Key 4: `Layer Switch`
     - Row 2: Key 7: `Left` | Key 8: `Down` | Key 9: `Right` | Key 10: `none`
   - **Dynamic Action Cluster (Keys 5, 6, 11, 12) across Layers:**
     - **Layer 0 (Core Navigation & Transport):** Key 5: `A` | Key 6: `B` | Key 11: `C` | Key 12: `D`
     - **Layer 1 (Context Actions & Recording):** Key 5: `E` | Key 6: `F` | Key 11: `G` | Key 12: `H`
     - **Layer 2 (Direct Screen Jumps):** Key 5: `I` | Key 6: `J` | Key 11: `K` | Key 12: `L`
     - **Layer 3 (Preset & Coarse Navigation):** Key 5: `M` | Key 6: `N` | Key 11: `O` | Key 12: `P`
     - **Layer 4 (Performance & System Utilities):** Key 5: `Q` | Key 6: `R` | Key 11: `S` | Key 12: `T`
4. **Key 4 Layer Status Beacon (RGB Visual Feedback):**
   - **Layer 0:** **No light (LED OFF)** — Immediate feedback that the pad is in primary base mode.
   - **Layer 1:** **Red light, slowly breathing / pulsating** (`#FF0000`).
   - **Layer 2:** **Green light, slowly breathing / pulsating** (`#00FF00`).
   - **Layer 3:** **Blue light, slowly breathing / pulsating** (`#0000FF`).
   - **Layer 4:** **Yellow light, slowly breathing / pulsating** (`#FFFF00`).

#### Step 4: Zynthian UI Keybindings Configuration (5-Layer Mappings)
Configured in Zynthian Webconf under **Interface** $\rightarrow$ **UI Keybindings** to enable complete autonomous navigation:

1. **Design Principles:**
   - **Always-Available D-Pad:** Directional navigation (`Up`, `Down`, `Left`, `Right`) is persistent across all layers, ensuring uninterrupted knob adjustment, cursor movement, and list scrolling.
   - **20 Discrete Action Triggers:** Keys `a` through `t` provide dedicated access to 20 Zynthian CUIA functions without holding awkward modifier combinations.

2. **Webconf UI Keybindings Assignment Table:**

| Key | Layer | Target CUIA Action | Function Description |
|---|---|---|---|
| **`Up`** | All | `ARROW_UP` | Turn focused knob up / scroll list up |
| **`Down`** | All | `ARROW_DOWN` | Turn focused knob down / scroll list down |
| **`Left`** | All | `ARROW_LEFT` | Select previous knob / move column left |
| **`Right`** | All | `ARROW_RIGHT` | Select next knob / move column right |
| **`a`** | Layer 0 | `BACK` (`ZYNSWITCH 1`) | Back / Cancel / Exit (Bold/Long hold opens Main Menu) |
| **`b`** | Layer 0 | `SELECT` (`ZYNSWITCH 3`) | Confirm / Enter / Open submenu / Select items |
| **`c`** | Layer 0 | `LAYER` (`ZYNSWITCH 0`) | Open Context / Chain Options Menu (Add FX, routing, clone, remove) |
| **`d`** | Layer 0 | `Pending` | Under review (e.g. Home/Mixer or dedicated Transport layer) |
| **`e`** | Layer 1 | `BOLD_SELECT` | Context options menu (Bold click / track options) |
| **`f`** | Layer 1 | `ALL_NOTES_OFF` | V5 Panic: Cut all hung MIDI notes |
| **`g`** | Layer 1 | `SCREEN_SNAPSHOT` | Open Snapshots & Presets view |
| **`h`** | Layer 1 | `TOGGLE_AUDIO_RECORD` | Start / Stop master stereo audio recording |
| **`i`** | Layer 2 | `SCREEN_AUDIO_MIXER` | Direct jump to Main Audio Mixer |
| **`j`** | Layer 2 | `SCREEN_PATTERN_EDITOR` | Direct jump to Step Sequencer / Pattern Editor |
| **`k`** | Layer 2 | `SCREEN_ADMIN` | Direct jump to Admin / System Settings |
| **`l`** | Layer 2 | `SCREEN_ALSA_MIXER` | Direct jump to Hardware ALSA Mixer levels |
| **`m`** | Layer 3 | `PREV_SNAPSHOT` | Load previous sound preset / subsnapshot |
| **`n`** | Layer 3 | `NEXT_SNAPSHOT` | Load next sound preset / subsnapshot |
| **`o`** | Layer 3 | `PAGE_UP` | Coarse knob jump (+10) / fast scroll up |
| **`p`** | Layer 3 | `PAGE_DOWN` | Coarse knob jump (-10) / fast scroll down |
| **`q`** | Layer 4 | `TEMPO` | Tap Tempo |
| **`r`** | Layer 4 | `METRONOME_TOGGLE` | Master metronome click track On / Off |
| **`s`** | Layer 4 | `TOGGLE_ALT_MODE` | Toggle V5 Alt Shift mode |
| **`t`** | Layer 4 | `POWER` | Open Power / Shutdown dialog |

#### Step 5: UI Options (Disable Mouse Pointer)
1. In Webconf, navigated to **Interface** $\rightarrow$ **UI Options**.
2. Enabled **Advanced** view mode.
3. Unselected **Mousepointer** to hide the visible cursor arrow from the touchscreen interface.
4. Clicked **Save**.

#### Step 6: Native Pisound Hardware Button ("The Button") Configuration
To map the Blokas Pisound hardware button (BCM GPIO 17 / Physical Pin 11 / WiringPi pin 0) natively without installing third-party packages or daemons:
- **Short press:** Open Admin Menu (`SCREEN_ADMIN`).
- **Long press / hold:** Open Power / Shutdown dialog (`POWER`).

##### 1. Webconf Configuration
Navigate to **Hardware** $\rightarrow$ **Audio & Hardware** (or **Wiring Layout**) in Zynthian Webconf (`https://zynthian.local`) and configure:

| Field | Setting |
|---|---|
| **Wiring Layout** | `Custom` |
| **Encoders A-pins** | `-1,-1,-1,-1` |
| **Encoders B-pins** | `-1,-1,-1,-1` |
| **Switches Pins** | `-1,-1,-1,-1,0` *(wPi 0 maps to BCM GPIO 17)* |
| **MCP23017 I2C Address** | *(empty)* |
| **MCP23017 INT-A Pin** | `Default` |
| **MCP23017 INT-B Pin** | `Default` |
| **Zynaptik Config** | *(empty)* |
| **Num. of Distance Sensors (TOF)** | `0` |
| **Customization Profile** | `V5` |

Under **Customizable Switches** $\rightarrow$ **Switch-1 Action**:
- **Switch-1 Action:** `Ui Action Release`
- **Short:** `Screen Admin`
- **Bold:** `Power`
- **Long:** `Power`
- Click **Save**.

##### 2. Terminal Configuration (Single Command Setup)
Open a terminal on the Raspberry Pi (via SSH as `root@zynthian.local` or through Webconf under **Interface** $\rightarrow$ **Terminal**) and run this command:

```bash
cat << 'EOF' > /zynthian/config/zynthian_custom_config.sh
# Blokas Pisound Button Mapping
# Under V5 profile / touch navigation, the physical button (GPIO 17) shifts to Custom Switch 25
export ZYNTHIAN_WIRING_CUSTOM_SWITCH_25="UI_ACTION_RELEASE"
export ZYNTHIAN_WIRING_CUSTOM_SWITCH_25__UI_SHORT="SCREEN_ADMIN"
export ZYNTHIAN_WIRING_CUSTOM_SWITCH_25__UI_LONG="POWER"
export ZYNTHIAN_WIRING_CUSTOM_SWITCH_25__UI_BOLD="POWER"
EOF
chmod +x /zynthian/config/zynthian_custom_config.sh
systemctl restart zynthian
```

##### 3. Technical Reason for the Terminal Override
- In Webconf, the form UI only displays `Switch-1 Action` (which writes to `ZYNTHIAN_WIRING_CUSTOM_SWITCH_01`).
- However, because **Customization Profile: V5** and **Touch Navigation** (`v5_keypad_left`) reserve 24 virtual switch slots (switches 4–27) for the on-screen touchscreen keypad buttons, Zynthian's runtime automatically shifts the 1st extra physical switch to switch index 28 ($4 + 24 = 28$).
- At runtime, switch index 28 evaluates to `custom_switch_ui_actions[28 - 4]` = **Custom Switch 25**.
- Creating `/zynthian/config/zynthian_custom_config.sh` binds the actions directly to `CUSTOM_SWITCH_25`. Because `zynthian.sh` automatically sources this file on every boot and UI restart after loading standard environment variables, the mapping is **100% permanent and completely immune to Webconf overwrites**.

##### 4. Verification & Testing
- **Short press:** Instantly toggles the Admin menu (`SCREEN_ADMIN`).
- **Long press / hold:** Instantly brings up the Power / Shutdown dialog (`POWER`).
- Verified persistent across full reboots.

#### Next Steps:
- Verify Pisound Audio In, MIDI In, and MIDI Out.
- Apply and verify macro keyboard live navigation.
