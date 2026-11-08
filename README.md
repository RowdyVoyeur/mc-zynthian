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
- [x] **Macro Keyboard Navigation:** Map the macro keyboard to be the primary navigation tool (see [`docs/sanyodevice-guide.md`](docs/sanyodevice-guide.md)). Implemented via single-layer EEPROM layout + background virtual layer daemon ([`scripts/layer-cake.py`](scripts/layer-cake.py)) providing 6 software layers (0–5), `Shift+Up`/`Shift+Down` switching, and native on-screen OSD layer notifications. *(Verified with virtual uinput driver)*
- [x] **Pisound Button Mapping:** Enable the physical button on the Pisound natively without extra packages (Short press: Admin Menu `SCREEN_ADMIN`, Long press: Power Menu `POWER`, see [`docs/pisound-guide.md`](docs/pisound-guide.md)). *(Verified working and persistent across reboots)*

### Stage 2: Enhanced Ecosystem
**Hardware:** Stage 1 + Roland MC-101 + Korg nanoKONTROL
**Goal:** Integrate external synthesizers and baseline physical control, achieving seamless audio/MIDI sync and deep hardware editing. Refer to the [Software Integration & Plugin Blueprint (`docs/software-integration.md`)](docs/software-integration.md) for the `mc101-ctrl.lv2` plugin, `mcee-audio.sh` multi-track audio daemon, and `scripts/kontroller.py` driver.

- [ ] **nanoKONTROL Integration:** Configure the Korg nanoKONTROL to drive Zynthian's transport controls, navigation, and primary system parameters (see [`docs/nanokontrol-guide.md`](docs/nanokontrol-guide.md) and [`docs/software-integration.md`](docs/software-integration.md)).
- [ ] **MC-101 USB MIDI Sync:** Ensure flawless MIDI IN/OUT via USB with the MC-101 (see [`docs/mc101-guide.md`](docs/mc101-guide.md)), allowing seamless clock synchronization.
- [x] **MC-101 USB Audio Transport:** Connect both master and per-track audio (IN and OUT) from the MC-101 to the Pi via USB at very low latency (via `scripts/mcee-audio.sh`, see [`docs/software-integration.md`](docs/software-integration.md)). *(Verified working in VENDOR mode with 4-channel playback and 10-channel capture; balanced stereo verified)*
- [x] **Dynamic Audio Routing:** Enable on-the-fly audio routing (preferably via the Zynthian UI) to patch Pisound inputs to the MC-101, Zynthian master to MC-101 inputs, MC-101 tracks to Zynthian effects, etc. *(Implemented via native Zynthian UI Chain Audio Routing / Snapshots and via `scripts/audio-flow.sh` 8-preset matrix)*
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
3. **Single Static Hardware Layout (Burned Once to EEPROM):**
   To eliminate physical multi-layer navigation issues and lack of on-screen feedback on the hardware, the SayoDevice is programmed with a **single, static physical layout** via WebHID (`https://app.sayodevice.com/`). All multi-layer switching is handled seamlessly in software by [`scripts/layer-cake.py`](scripts/layer-cake.py):
   - **Row 1:** Key 1: `none` | Key 2: `Up` | Key 3: `none` | Key 4: `Left Shift` | Key 5: `a` | Key 6: `b`
   - **Row 2:** Key 7: `Left` | Key 8: `Down` | Key 9: `Right` | Key 10: `none` | Key 11: `c` | Key 12: `d`

4. **Background Virtual Layer Daemon ([`scripts/layer-cake.py`](scripts/layer-cake.py)):**
   - **6 Software Layers (0 to 5):** Configurable in Python, easily extensible.
   - **Directional Navigation:** `Up`, `Down`, `Left`, `Right` remain persistent across all layers for cursor navigation, knob adjustment, and list scrolling.
   - **Two-Way Layer Switching:**
     - **`Shift + Up` (Key 4 + Key 2):** Cycles to the **next layer** ($0 \to 1 \to 2 \to 3 \to 4 \to 5 \to 0$).
     - **`Shift + Down` (Key 4 + Key 8):** Cycles to the **previous layer** ($1 \to 0 \to 5 \to 4 \to 3 \to 2 \dots$).
   - **Dynamic Action Cluster (Keys 5, 6, 11, 12):**
     - **Layer 0:** Key 5: `a` | Key 6: `b` | Key 11: `c` | Key 12: `d`
     - **Layer 1:** Key 5: `e` | Key 6: `f` | Key 11: `g` | Key 12: `h`
     - **Layer 2:** Key 5: `i` | Key 6: `j` | Key 11: `k` | Key 12: `l`
     - **Layer 3:** Key 5: `m` | Key 6: `n` | Key 11: `o` | Key 12: `p`
     - **Layer 4:** Key 5: `q` | Key 6: `r` | Key 11: `s` | Key 12: `t`
     - **Layer 5:** Key 5: `u` | Key 6: `v` | Key 11: `w` | Key 12: `x`
   - **Native Floating On-Screen Display (OSD):**
     - Renders a floating notification banner on Zynthian's LCD (`DISPLAY=:0`) for 1.8 seconds whenever the layer changes.
     - Displays the active layer name and a reminder of all 4 mapped actions (e.g., `◆ LAYER 1: CONTEXT ACTIONS & RECORDING ◆` with `[E] Bold Select • [F] Panic • [G] Snapshots • [H] Rec Audio`).

5. **Daemon Service Setup (Starts on Boot & Survives Updates):**
   ```bash
   # 1. Install standard Linux input event dependency (if not present)
   apt-get update && apt-get install -y python3-evdev

   # 2. Install the persistent systemd service
   cat << 'EOF' > /etc/systemd/system/layer-cake.service
   [Unit]
   Description=SayoDevice 12-Key Virtual Layer Daemon with OSD (layer-cake)
   After=zynthian.service display-manager.service
   Wants=zynthian.service

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/zynthian/mc-zynthian
   ExecStart=/usr/bin/python3 /zynthian/mc-zynthian/scripts/layer-cake.py
   Restart=always
   RestartSec=2
   Environment=DISPLAY=:0

   [Install]
   WantedBy=multi-user.target
   EOF

   # 3. Enable and start daemon
   systemctl daemon-reload
   systemctl enable --now layer-cake.service
   ```

#### Step 4: Zynthian UI Keybindings Configuration (6-Layer Mappings)
Configured in Zynthian Webconf under **Interface** $\rightarrow$ **UI Keybindings** to enable complete autonomous navigation:

| Key | Layer | Target CUIA Action | Function Description |
|---|---|---|---|
| **`Up`** | All | `ARROW_UP` | Turn focused knob up / scroll list up |
| **`Down`** | All | `ARROW_DOWN` | Turn focused knob down / scroll list down |
| **`Left`** | All | `ARROW_LEFT` | Select previous knob / move column left |
| **`Right`** | All | `ARROW_RIGHT` | Select next knob / move column right |
| **`a`** | Layer 0 | `BACK` (`ZYNSWITCH 1`) | Back / Cancel / Exit (Bold/Long hold opens Main Menu) |
| **`b`** | Layer 0 | `SELECT` (`ZYNSWITCH 3`) | Confirm / Enter / Open submenu / Select items |
| **`c`** | Layer 0 | `LAYER` (`ZYNSWITCH 0`) | Open Context / Chain Options Menu (Add FX, routing, clone, remove) |
| **`d`** | Layer 0 | `SCREEN_AUDIO_MIXER` | Jump directly to Main Audio Mixer |
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
| **`u`** | Layer 5 | `TOGGLE_PLAY` | Start / Stop Sequencer playback |
| **`v`** | Layer 5 | `TOGGLE_MIDI_RECORD` | Toggle MIDI sequence recording |
| **`w`** | Layer 5 | `PREV_TRACK` | Select previous active chain / track |
| **`x`** | Layer 5 | `NEXT_TRACK` | Select next active chain / track |

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

##### 5. Post-Software-Update Maintenance
> [!IMPORTANT]
> **Re-saving Wiring Layout After Software Updates:**
> Zynthian OS software updates (`update_zynthian.sh` or Webconf updates) can reset or unbind the custom hardware wiring layout in Webconf. 
> While `/zynthian/config/zynthian_custom_config.sh` remains safely preserved on disk, GPIO 17 will not register button presses if the `Switches Pins` field is cleared.
> **Fix after an update:** Navigate to Webconf **Hardware $\rightarrow$ Audio & Hardware** (or **Wiring Layout**), verify **Wiring Layout** is set to `Custom` with **Switches Pins** set to `-1,-1,-1,-1,0`, and click **Save**. The button will immediately return to life without needing to re-run any terminal commands.

### Stage 2: Enhanced Ecosystem Setup

#### Step 7: Roland MC-101 USB Audio Bridge & Dynamic Audio Routing Setup

The Roland MC-101 operates as a multi-channel USB soundcard under Linux when set to `VENDOR` mode ([`docs/mc101-guide.md`](docs/mc101-guide.md)). The audio transport is bridged into JACK via [`scripts/mcee-audio.sh`](scripts/mcee-audio.sh), providing 10 capture channels (stems out of MC-101) and 4 playback channels (audio into MC-101).

Audio routing between Zynthian and the MC-101 is managed through two complementary methods: native Zynthian UI workflows and the automated preset router [`scripts/audio-flow.sh`](scripts/audio-flow.sh).

##### 1. Managing Audio Connections Inside Zynthian UI (Screen / Webconf)

1. **Routing Individual Chains / Synthesizers to MC-101 Channels:**
   - In the Zynthian UI, highlight a chain (or long-click the chain / press Key `c` for Chain Options).
   - Select **Audio Routing**.
   - By default, chains are routed to the **Main Mix Bus** (`zynmixer_bus`).
   - In this menu, you can re-route any chain directly to:
     - **`MC101_out:playback_1/2`**: Sends the synth dry into MC-101 Master Return (sums directly to MC-101 headphones/main out).
     - **`MC101_out:playback_3/4` (`PC IN`)**: Sends the synth directly into the MC-101's audio insert path. On the MC-101, select any track (e.g. Track 1), enter `[SHIFT] + [TRACK SEL]` $\rightarrow$ `GEN` $\rightarrow$ set `Insert = PC IN`. The Zynthian synth will now be processed through that track's MFX, 3-band EQ, and fader!
2. **Routing MC-101 Tracks into Zynthian Effect Chains:**
   - In Zynthian UI, tap `+` to add a new chain and choose **Audio In**.
   - In the input selection list, select `MC101_in:capture_1/2` (for the full MC-101 master mix) or `MC101_in:capture_3/4` (for isolated Track 1).
   - Add any desired audio effect plugins to this chain (e.g. MOD-UI, Guitarix, Calf Reverb, sidechain compressors).
   - MC-101 audio now streams through Zynthian's effects processor and out to Pisound or headphones.
3. **Saving & Recalling Routings via Master Snapshots (`.zss`):**
   - Once an audio routing configuration is established, save it as a **Master Snapshot** (press Key `o` or navigate to **Snapshot** menu).
   - Create distinct snapshots for different workflows (e.g., `01_MC101_MasterMix`, `02_MC101_PC_Insert`, `03_MC101_Track1_ZynFX`).
   - Snapshots restore complete audio patchings, chain levels, and synth presets in under 2 seconds. They can be triggered from the touchscreen, macro keyboard, or MIDI Program Change.

##### 2. Managing Audio Routing via Script (`scripts/audio-flow.sh`)

[`scripts/audio-flow.sh`](scripts/audio-flow.sh) provides dynamic, on-the-fly JACK patching modeled after the multi-preset architecture of `mc101-pisound`, replacing Dirtywave M8 with Zynthian:

| Preset | Routing Name | Signal Flow Summary |
|---|---|---|
| **1** | `zyn-to-mc101` | Zynthian Master $\rightarrow$ MC-101 Master Return (`playback_1/2`). Standard listening on MC-101 phones. |
| **2** | `zyn-and-in-to-mc101` | Zynthian Master $\rightarrow$ MC-101 Master Return + Pisound Line In $\rightarrow$ MC-101 `PC IN` (`playback_3/4` for Track MFX). |
| **3** | `dual-mix-out` | MC-101 Master + Zynthian Master $\rightarrow$ Pisound Out (Parallel mix on Pisound main analog out). |
| **4** | `mc101-thru-zynfx` | MC-101 Master $\rightarrow$ Zynthian Audio In / FX Chain $\rightarrow$ Pisound Out. |
| **5** | `serial-rig` | Pisound Line In $\rightarrow$ MC-101 `PC IN` $\rightarrow$ MC-101 Master $\rightarrow$ Zynthian FX $\rightarrow$ Pisound Out. |
| **6** | `parallel-in-and-zyn` | Pisound Line In $\rightarrow$ MC-101 `PC IN` + Zynthian Master + MC-101 Master $\rightarrow$ Pisound Out. |
| **7** | `zynfx-to-mc101` | Pisound Line In $\rightarrow$ Zynthian FX $\rightarrow$ MC-101 `PC IN` $\rightarrow$ MC-101 Master $\rightarrow$ Pisound Out. |
| **8** | `split-stem` | Split Stems: Zynthian Chain 0 $\rightarrow$ MC-101 `PC IN`, Zynthian Master $\rightarrow$ MC-101 Master Return, MC-101 Track 1 $\rightarrow$ Pisound Out. |

##### 3. Script CLI Usage Examples

```bash
# Apply a specific preset (1 to 8)
./scripts/audio-flow.sh 1

# Cycle sequentially through presets 1 -> 8 (can be bound to a macro key or daemon)
./scripts/audio-flow.sh cycle

# Reset to safe default (Preset 1)
./scripts/audio-flow.sh reset

# Inspect active JACK audio connections and detected chains
./scripts/audio-flow.sh status

# Route a specific Zynthian chain (by ID) to MC-101 PC IN (Audio Insert for Track MFX)
./scripts/audio-flow.sh route-chain 0 pcin

# Route a specific chain and isolate it (unlinks from Zynthian Master Bus to avoid doubling)
./scripts/audio-flow.sh route-chain 0 pcin --isolate

# Route a specific instrument by engine name pattern
./scripts/audio-flow.sh route-chain JC303 pcin

# Route MC-101 Track 1 isolated direct output (capture_3/4) into Zynthian FX
./scripts/audio-flow.sh route-track 1 zynfx
```

#### Next Steps:
- Verify Pisound Audio In, MIDI In, and MIDI Out.
- Apply and verify macro keyboard live navigation.
