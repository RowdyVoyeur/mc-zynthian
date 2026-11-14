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
- [x] **Macro Keyboard Navigation:** Map the macro keyboard to be the primary navigation tool (see [`docs/sanyodevice-guide.md`](docs/sanyodevice-guide.md)). Implemented via single-layer EEPROM layout + background virtual layer daemon ([`scripts/layer-cake.py`](scripts/layer-cake.py)) providing 8 directly selectable software layers (1–8), `Shift + Key` switching, and native title-bar OSD layer notifications. *(Verified with virtual uinput driver)*
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
   - **8 Directly Selectable Layers:** Hold `Shift` (Key 4) and press a key to jump straight to a layer. Shift itself is never forwarded to Zynthian.
     | Layer | Select with | Key 5 (`a`) | Key 6 (`b`) | Key 11 (`c`) | Key 12 (`d`) | Role |
     |---|---|---|---|---|---|---|
     | 1 | `Shift + Up` | `a` | `b` | `c` | `d` | Main |
     | 2 | `Shift + Down` | `a` | `b` | `e` | `f` | Main |
     | 3 | `Shift + Left` | `a` | `b` | `g` | `h` | Main |
     | 4 | `Shift + Right` | `a` | `b` | `i` | `j` | Main |
     | 5 | `Shift + A` | `a` | `b` | `k` | `l` | Main |
     | 6 | `Shift + B` | `a` | `b` | `m` | `n` | Main |
     | 7 | `Shift + C` | `o` | `p` | `q` | `r` | Secondary (parameter editing) |
     | 8 | `Shift + D` | `s` | `t` | `u` | `v` | Secondary (parameter editing) |
   - **Fixed keys:** Arrow keys always pass through unchanged. On Layers 1–6, `a` and `b` are always emitted (intended for Knob 2 and Knob 4 in Webconf); `c`/`d` change per layer (intended for hardware buttons such as Mix, Alt, etc.).
   - **Title Bar Overlay:** A single line covering Zynthian's title bar (same height, Zynthian UI font, white on black) appears for 1.8 s when Shift is pressed or the layer changes, e.g. `3: [A] Knob 2 | [B] Knob 4 | [C] Btn C3 | [D] Btn D3`. Labels are placeholders until the final per-layer actions are chosen.
   - Includes an automatic X11 boot retry loop to ensure graceful startup on system boot.

5. **Daemon Service Setup (Starts on Boot & Survives Updates):**
   ```bash
   # 1. Install standard Linux input event dependency (if not present)
   apt-get update && apt-get install -y python3-evdev

   # 2. Ensure script is executable
   chmod +x /root/mc-zynthian/scripts/layer-cake.py

   # 3. Install the persistent systemd service
   cat << 'EOF' > /etc/systemd/system/layer-cake.service
   [Unit]
   Description=SayoDevice 12-Key Virtual Layer Daemon with OSD (layer-cake)
   After=zynthian.service sound.target
   Wants=zynthian.service

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/mc-zynthian
   ExecStart=/root/mc-zynthian/scripts/layer-cake.py
   Restart=always
   RestartSec=3
   Environment=DISPLAY=:0
   Environment=XAUTHORITY=/root/.Xauthority

   [Install]
   WantedBy=multi-user.target
   EOF

   # 4. Enable and start daemon
   systemctl daemon-reload
   systemctl enable --now layer-cake.service

   # 5. Check live status
   systemctl status layer-cake.service
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

#### Step 7: Roland MC-101 USB Audio Bridge & Native Zynthian UI Audio Routing

The Roland MC-101 operates as a multi-channel USB soundcard under Linux when set to `VENDOR` mode ([`docs/mc101-guide.md`](docs/mc101-guide.md)). The audio transport is bridged into JACK via [`scripts/mcee-audio.sh`](scripts/mcee-audio.sh), providing 10 capture channels (stems out of MC-101) and 4 playback channels (audio into MC-101).

Because Zynthian's internal audio router (`zynthian_autoconnect`) discovers external USB audio bridges by looking for JACK clients prefixed with **`zynain`** (capture) and **`zynaout`** (playback), `scripts/mcee-audio.sh` registers its bridges as **`zynain_mc101`** and **`zynaout_mc101`** and sets human-readable JACK port aliases on all 14 channels. This makes every MC-101 track and input appear directly inside Zynthian's native **Audio In** and **Audio Out** chain menus, and ensures all routings are saved and restored in Zynthian Snapshots (`.zss`).

##### 1. Installing & Enabling the Persistent Audio Bridge Service (`mcee-audio.service`)

```bash
# 1. Ensure scripts are executable
chmod +x /root/mc-zynthian/scripts/mcee-audio.sh /root/mc-zynthian/scripts/audio-flow.sh

# 2. Install the persistent systemd service
cat << 'EOF' > /etc/systemd/system/mcee-audio.service
[Unit]
Description=Roland MC-101 10-In/4-Out ALSA-JACK Bridge with Zynthian UI Aliases
After=zynthian.service sound.target
Wants=zynthian.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/mc-zynthian
ExecStart=/root/mc-zynthian/scripts/mcee-audio.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 3. Enable and start the service
systemctl daemon-reload
systemctl enable --now mcee-audio.service
```

##### 2. Native Zynthian UI Port Map (`Chain Options` $\rightarrow$ `Audio In` / `Audio Out`)

With Pisound as the primary 2-in / 2-out soundcard (`Inputs 1–2` and `Outputs 1–2`), the MC-101 channels appear in Zynthian's native UI menus as:

| Zynthian UI Menu | Menu Entry Displayed on Screen | JACK Port | Signal Path |
|---|---|---|---|
| **Audio In** | `Input 1` / `Input 2` | `system:capture_1/2` | Pisound Hardware Line In L/R |
| **Audio In** | `Input 3 (MC-101 Master L)` / `Input 4 (MC-101 Master R)` | `zynain_mc101:capture_1/2` | MC-101 Master Stereo Out $\rightarrow$ Zynthian |
| **Audio In** | `Input 5 (MC-101 Track 1 L)` / `Input 6 (MC-101 Track 1 R)` | `zynain_mc101:capture_3/4` | MC-101 Track 1 Direct Out $\rightarrow$ Zynthian |
| **Audio In** | `Input 7 (MC-101 Track 2 L)` / `Input 8 (MC-101 Track 2 R)` | `zynain_mc101:capture_5/6` | MC-101 Track 2 Direct Out $\rightarrow$ Zynthian |
| **Audio In** | `Input 9 (MC-101 Track 3 L)` / `Input 10 (MC-101 Track 3 R)` | `zynain_mc101:capture_7/8` | MC-101 Track 3 Direct Out $\rightarrow$ Zynthian |
| **Audio In** | `Input 11 (MC-101 Track 4 L)` / `Input 12 (MC-101 Track 4 R)` | `zynain_mc101:capture_9/10` | MC-101 Track 4 Direct Out $\rightarrow$ Zynthian |
| **Audio Out** | `Outputs 1+2 (stereo)` | `system:playback_1/2` | Zynthian $\rightarrow$ Pisound Hardware Out L/R |
| **Audio Out** | `Outputs 3+4 (stereo)` / `Output 3/4 (MC-101 Master In L/R)` | `zynaout_mc101:playback_1/2` | Zynthian $\rightarrow$ MC-101 Master Mix Return |
| **Audio Out** | `Outputs 5+6 (stereo)` / `Output 5/6 (MC-101 PC IN L/R)` | `zynaout_mc101:playback_3/4` | Zynthian $\rightarrow$ MC-101 `PC IN` (Track Insert / MFX) |

##### 3. Step-by-Step Native Zynthian UI Routing Workflows

1. **Route MC-101 Track 4 (or Track 1–4) $\rightarrow$ Zynthian Track/Chain 4:**
   - Create or select an Audio/FX Chain on Zynthian (e.g., Chain 4).
   - Open **Chain Options** (bold-press `SELECT` on the chain strip in Mixer view) $\rightarrow$ select **Audio In**.
   - Uncheck `Input 1` and `Input 2` (Pisound) and check **`Input 11 (MC-101 Track 4 L)`** and **`Input 12 (MC-101 Track 4 R)`**.
   - Isolated audio from MC-101 Track 4 now streams directly into Zynthian Chain 4's effects and mixer fader.
2. **Route Zynthian Track/Chain 1 $\rightarrow$ MC-101 Track 1 (or any MC-101 Track MFX):**
   - Select Chain 1 on Zynthian, open **Chain Options** $\rightarrow$ select **Audio Out**.
   - Under `> AUDIO OUTPUT`, check **`Outputs 5+6 (stereo)`** (which corresponds to `Output 5 (MC-101 PC IN L)` + `Output 6 (MC-101 PC IN R)`).
   - *(Optional)* Uncheck **`Main mixbus`** at the top of the list if you want Chain 1 isolated so it only goes into the MC-101 and does not double in Zynthian's Main mix.
   - On the MC-101 hardware, hold `[SHIFT]` + press `[TRACK SEL 1]` $\rightarrow$ `GEN` tab $\rightarrow$ set **`Insert = PC IN`** (or `PC IN L` / `PC IN R`). Zynthian Chain 1 now flows directly through MC-101 Track 1's MFX, 3-band EQ, and fader.
3. **Route Zynthian Master (`Main`) $\rightarrow$ MC-101 `PC IN` or `Master In`:**
   - Highlight the **`Main`** mixbus strip on the far right of Zynthian's Audio Mixer, open **Chain Options** $\rightarrow$ select **Audio Out**.
   - Check **`Outputs 3+4 (stereo)`** to send Zynthian Master into **MC-101 Master Return**, or check **`Outputs 5+6 (stereo)`** to send Zynthian Master into **MC-101 `PC IN`** (and uncheck `Outputs 1+2 (stereo)` if you do not want it on Pisound Out).
4. **Route MC-101 Master $\rightarrow$ Zynthian Master / FX Chain:**
   - Create an Audio Chain on Zynthian, open **Chain Options** $\rightarrow$ **Audio In**, and check **`Input 3 (MC-101 Master L)`** and **`Input 4 (MC-101 Master R)`**.
5. **Saving & Recalling Routings via Snapshots (`.zss`):**
   - Because `zynain_mc101` and `zynaout_mc101` are managed natively by `zynthian_autoconnect`, saving a **Snapshot** automatically stores all per-chain Audio In and Audio Out checkboxes and restores them on load.

##### 4. Optional CLI Preset Router (`scripts/audio-flow.sh`)

For quick command-line inspection or scripted JACK patching outside the GUI, [`scripts/audio-flow.sh`](scripts/audio-flow.sh) also works with the `zynain_mc101` / `zynaout_mc101` bridges:

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
