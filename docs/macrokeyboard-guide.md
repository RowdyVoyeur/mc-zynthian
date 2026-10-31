# SayoDevice 12-Key Macro Keyboard: Zynthian Controller Guide & Reference Manual

Comprehensive technical specification, web configuration guide, and Zynthian integration manual for the **SayoDevice 12-Key USB Macro Keyboard** (customized in a 9-key retro game controller layout).

This document serves as the foundational guide for Stage 1 of the [`mc-zynthian`](../README.md) project, fulfilling the core architectural requirement: **enabling full autonomous navigation of the Zynthian UI via tactile physical controls, making the touchscreen an optional assist**.

---

## 1. Hardware Architecture & Physical Matrix Layout

The macro controller is based on the **SayoDevice 12-Key programmable USB keypad** (Sayobot / WebHID ecosystem). 

The underlying circuit board contains a **$2 \times 6$ matrix (2 rows of 6 keys)** of 12 mechanical key switches with individual per-key RGB backlighting. The custom physical enclosure deliberately exposes **9 functional keys** by masking/disabling 3 keys (Keys 1, 3, and 10), creating a classic retro game console layout with a cross D-pad on the left and action/system buttons on the right:

```
+---------------------------------------------------------------------------------------------------------------------------------------+
|  [ Key 1: HIDDEN ]   [ Key 2: UP ]       [ Key 3: HIDDEN ]   [ Key 4: SHIFT ]       [ Key 5: A ]            [ Key 6: B ]              | (Row 1)
|  (Internal/Masked)   (D-Pad Up)          (Internal/Masked)   (Layer Modifier)       (Action A / Select)     (Action B / Back)         |
|                                                                                                                                       |
|  [ Key 7: LEFT ]     [ Key 8: DOWN ]     [ Key 9: RIGHT ]    [ Key 10: HIDDEN ]     [ Key 11: SELECT ]      [ Key 12: START ]         | (Row 2)
|  (D-Pad Left)        (D-Pad Down)        (D-Pad Right)       (Internal/Masked)      (Screen / Menu / Enter) (Transport / Spacebar)    |
+---------------------------------------------------------------------------------------------------------------------------------------+
| <----------------- LEFT CLUSTER: CROSS D-PAD -----------------> | <------------------ RIGHT CLUSTER: RETRO CONSOLE -----------------> |
```

### 1.1 Complete 12-Key ($2 \times 6$) Hardware Matrix Breakdown

Numbering from **Left to Right across Row 1, then Left to Right across Row 2**:

#### Row 1 (Keys 1 through 6)
| Key # | Position | Hardware Status | Faceplate Label | Primary Role | Default Keycode Example |
|---|---|---|---|---|---|
| **Key 1** | Row 1, Col 1 | **Hidden / Disabled** | — | Top-Left Corner Mask | Disabled (`No Key`) |
| **Key 2** | Row 1, Col 2 | **Exposed** | `UP` | D-Pad Up | `Key: Up Arrow` |
| **Key 3** | Row 1, Col 3 | **Hidden / Disabled** | — | Top-Right Corner Mask | Disabled (`No Key`) |
| **Key 4** | Row 1, Col 4 | **Exposed** | `SHIFT` | Layer Modifier (Fn) | SayoDevice `Layer Switch (Fn)` |
| **Key 5** | Row 1, Col 5 | **Exposed** | `A` | Action A / Confirm | `Key: Enter` / `Return` |
| **Key 6** | Row 1, Col 6 | **Exposed** | `B` | Action B / Cancel | `Key: Escape` / `Backspace` |

#### Row 2 (Keys 7 through 12)
| Key # | Position | Hardware Status | Faceplate Label | Primary Role | Default Keycode Example |
|---|---|---|---|---|---|
| **Key 7** | Row 2, Col 1 | **Exposed** | `LEFT` | D-Pad Left | `Key: Left Arrow` |
| **Key 8** | Row 2, Col 2 | **Exposed** | `DOWN` | D-Pad Down | `Key: Down Arrow` |
| **Key 9** | Row 2, Col 3 | **Exposed** | `RIGHT` | D-Pad Right | `Key: Right Arrow` |
| **Key 10**| Row 2, Col 4 | **Hidden / Disabled** | — | Bottom-Left System Mask | Disabled (`No Key`) |
| **Key 11**| Row 2, Col 5 | **Exposed** | `SELECT` | System Screen / Confirm | `Key: Tab` (or `Enter`) |
| **Key 12**| Row 2, Col 6 | **Exposed** | `START` | Master Transport | `Key: Space` (Play/Stop) |

### 1.2 Full Mapping Flexibility
> [!NOTE]
> **Arbitrary Key Assignment:**
> The key assignments listed above are baseline operational recommendations. In SayoDevice hardware, **each individual key can be programmed to ANY arbitrary keyboard character, function key, media command, or combination of modifier keystrokes**:
> - `Key 12 (START)` can be mapped to `Spacebar` (standard DAW transport toggle) or any desired shortcut.
> - `Key 11 (SELECT)` can be mapped to `Tab` (switching chains/screens), `F1`–`F4`, or directly to `Enter` (selection confirmation).
> - `Key 5 (A)` and `Key 6 (B)` can be mapped to `Enter`/`Escape` or customized to `Ctrl+Enter`, `Z`, `X`, etc.
>
> All configuration is performed via the WebHID interface and committed to internal EEPROM.

### 1.3 Electrical & Microcontroller Specifications
- **Host Interface**: USB 2.0 Full-Speed Type-C / Micro-B, class-compliant USB HID keyboard.
- **Power Consumption**: $5\text{V}$ USB bus powered, drawing $< 80\text{ mA}$ (fully operable from Raspberry Pi 4 USB ports).
- **Onboard Microcontroller**: High-efficiency USB microcontroller (typically CH55x or RP2040) with internal non-volatile EEPROM/Flash storage.
- **Zero-Driver Operation**: Once programmed via the WebHID configurator, all key assignments, macros, and RGB lighting configurations are stored permanently in internal hardware memory. The device connects to Linux/Zynthian as a **standard driverless USB HID keyboard**.
- **Retroillumination (RGB Backlighting)**: Every individual key features a surface-mount programmable RGB LED capable of static color coding, reactive key-press illumination, breathing effects, and layer-status feedback. (Hidden Keys 1, 3, and 10 can have their RGB LEDs turned completely OFF to prevent internal light leakage).

---

## 2. Configuration via SayoDevice WebHID

Because the hardware contains no onboard LCD screen or physical configuration DIP switches, all key assignments, layers, and RGB backlighting are configured using the official browser-based WebHID portal.

### 2.1 Essential Configuration Links
- **Official WebHID Configuration App**: [sayodevice.com](https://sayodevice.com/)
- **Official Documentation**: [SayoDevice WebHID Documentation](https://manual.sayodevice.com/#/en/docs/std/web_hid/README)
- **Source Repository & Firmware**: [Sayobot/SayoDevice_manual GitHub](https://github.com/Sayobot/SayoDevice_manual)

### 2.2 System & Browser Requirements
> [!IMPORTANT]
> **Browser Compatibility:**
> The SayoDevice configurator utilizes the **WebHID API**, which allows direct low-level USB communication from the browser without installing desktop software.
> - **Supported Browsers**: Google Chrome, Microsoft Edge, Brave, Opera, or any modern Chromium-based browser.
> - **Unsupported**: Mozilla Firefox and Apple Safari do not natively support WebHID and will not connect to the device.

### 2.3 Step-by-Step Programming Walkthrough

```
+---------------------------------------------------------------------------------------------------+
| 1. Connect Device  ---> 2. Open sayodevice.com ---> 3. Pair WebHID Window ---> 4. Map Keys/Layers|
|                                                                                     |             |
| 5. Unplug & Deploy <--- 6. Reconnect to Pi     <--- 5. Save to Flash/EEPROM <-------+             |
+---------------------------------------------------------------------------------------------------+
```

1. **Connect to Programming Machine**:
   - Plug the macro keyboard into your PC/Mac workstation using a USB data cable.
2. **Access the Configurator**:
   - Launch Google Chrome or Microsoft Edge and navigate to `https://sayodevice.com/`.
3. **Establish WebHID Handshake**:
   - Click the green **"Search Sayo-Device"** or **"Connect"** button on the homepage.
   - A browser security popup will display detected USB HID devices.
   - Select your device (typically listed as `SayoDevice` or `SayoDevice O3C/12K`) and click **"Connect"**.
   - The web interface will read the hardware's internal memory and display the current key mapping matrix.
4. **Configure Key Codes & Layers**:
   - Select each physical key on the virtual pad diagram.
   - Assign the corresponding Standard Keyboard Scan Codes (see Section 3 for recommended Zynthian mappings).
   - Configure **Layer 0** (Default) and **Layer 1** (Shifted).
   - Set the `SHIFT` physical button behavior to **`Momentary Layer Switch (Fn)`** or **`Layer Toggle`**.
5. **Configure RGB Retroillumination**:
   - Open the **Lighting** tab.
   - Set color palettes for each key to visually identify functional clusters (see Section 4).
6. **Commit Configuration to Hardware**:
   - Click **"Save"** or **"Write to Device"**.
   - Wait for the confirmation prompt indicating the EEPROM write has succeeded.
   - Disconnect the keyboard. The device is now permanently configured and ready for Zynthian!

---

## 3. Dual-Layer Zynthian Navigation Scheme

To fulfill the project goal of operating Zynthian completely without a touchscreen or external MIDI controller, the 9 exposed keys are mapped across two operational layers using the `SHIFT` modifier:

### 3.1 Layer 0: Primary UI Navigation & Transport (Default Mode)
Active during standard performance and menu navigation:

| Key # | Faceplate Label | Physical Role | Recommended Keycode | Alternative Options | Zynthian UI Function | CUIA Command |
|---|---|---|---|---|---|---|
| **Key 2** | `UP` | D-Pad Top | `Key: Up Arrow` | `Key: Page Up` / `+` | Move selection up in lists | `ARROW_UP` |
| **Key 8** | `DOWN` | D-Pad Bottom | `Key: Down Arrow` | `Key: Page Down` / `-`| Move selection down in lists | `ARROW_DOWN` |
| **Key 7** | `LEFT` | D-Pad Left | `Key: Left Arrow` | `Key: [` / `,` | Navigate left / previous item | `ARROW_LEFT` |
| **Key 9** | `RIGHT` | D-Pad Right | `Key: Right Arrow` | `Key: ]` / `.` | Navigate right / next item | `ARROW_RIGHT` |
| **Key 5** | `A` | Action A | `Key: Enter` / `Return` | `Key: Z` / `Ctrl+Enter`| **Select / Confirm / Open Menu** | `SELECT` |
| **Key 6** | `B` | Action B | `Key: Escape` / `Backspace` | `Key: X` / `Back` | **Back / Cancel / Exit Menu** | `BACK` |
| **Key 11**| `SELECT` | System Select | `Key: Tab` / `F1` | `Key: Enter` / `F3` | Cycle active synth chain / switch layer | `SWITCH_CHAIN` |
| **Key 12**| `START` | System Start | `Key: Space` | `Key: Enter` / `P` | **Transport Play / Stop Toggle** | `TOGGLE_PLAY` |
| **Key 4** | `SHIFT` | Layer Modifier | SayoDevice `Fn` | `Left Shift` / `Layer 1`| Hold to access Layer 1 | — |
| **1, 3, 10** | *HIDDEN* | Unexposed PCB | `Disabled` (`None`) | — | Unassigned / No keystroke | — |

---

### 3.2 Layer 1: Deep Editing, Mixer & Sound Management (Shifted Mode)
Activated while holding **`Key 4 (SHIFT)`**:

| Shifted Combination | Recommended Keycode | Alternative Options | Zynthian UI Function | CUIA Command |
|---|---|---|---|---|
| **`SHIFT` + `Key 2 (UP)`** | `Key: Page Up` | `Key: +` / Volume Up | Coarse parameter increment / Fast scroll | `PAGE_UP` |
| **`SHIFT` + `Key 8 (DOWN)`** | `Key: Page Down` | `Key: -` / Volume Down| Coarse parameter decrement / Fast scroll | `PAGE_DOWN` |
| **`SHIFT` + `Key 7 (LEFT)`** | `Key: [` (Bracket Left) | `Key: Home` / Prev Bank| Load **Previous Preset / Snapshot** | `PREV_SNAPSHOT` |
| **`SHIFT` + `Key 9 (RIGHT)`** | `Key: ]` (Bracket Right)| `Key: End` / Next Bank | Load **Next Preset / Snapshot** | `NEXT_SNAPSHOT` |
| **`SHIFT` + `Key 5 (A)`** | `Key: Shift + Enter` | `Key: F10` / Menu Key | **Bold / Long Click** (Context Menu) | `BOLD_SELECT` |
| **`SHIFT` + `Key 6 (B)`** | `Key: Delete` / `Ctrl+Esc`| `Key: F12` | **MIDI Panic / All Notes Off** | `ALL_NOTES_OFF` |
| **`SHIFT` + `Key 11 (SELECT)`**| `Key: F2` | `Key: M` / `F5` | Jump directly to **Zynmixer Screen** | `SCREEN_MIXER` |
| **`SHIFT` + `Key 12 (START)`** | `Key: R` / `Ctrl+Space`| `Key: *` (Numpad) | **Toggle MIDI Recording / Overdub** | `TOGGLE_MIDI_RECORD` |
| **`SHIFT` + `Key 4 (SHIFT)`** | — | — | Layer 1 Active Feedback | — |

---

## 4. Retroillumination (RGB Backlighting) Design

The SayoDevice's individual per-key RGB backlighting transforms the macro keyboard from a passive input device into an intuitive visual dashboard.

```
Row 1: [ Key 1: OFF ]        [ Key 2 (UP): Cyan ]   [ Key 3: OFF ]         [ Key 4 (SHIFT): Purple ] [ Key 5 (A): Green ]      [ Key 6 (B): Red ]
Row 2: [ Key 7 (LEFT): Cyan] [ Key 8 (DOWN): Cyan ] [ Key 9 (RIGHT): Cyan] [ Key 10: OFF ]           [ Key 11 (SELECT): Gold ] [ Key 12 (START): Magenta ]
```

### 4.1 Recommended Functional Color Palette

| Key Matrix Identifier | Functional Group | Recommended Color | Hex Code | Visual Psychology & Functional Meaning |
|---|---|---|---|---|
| **Keys 2, 7, 8, 9** | **D-Pad Cluster (`UP`, `LT`, `DN`, `RT`)** | **Ice Blue / Cyan** | `#00E5FF` | Calm directional navigation cluster. |
| **Key 5** | **Action `A` (Confirm / Enter)** | **Emerald Green** | `#00E676` | Affirmative action, load, confirm, and execute. |
| **Key 6** | **Action `B` (Back / Cancel)** | **Crimson Red** | `#FF1744` | Negative action, escape, back out, and cancel. |
| **Key 11** | **System `SELECT` (View / Mode)** | **Amber Gold** | `#FFD600` | System navigation, mode cycling, and channel selection. |
| **Key 12** | **System `START` (Transport Play)** | **Vibrant Magenta** | `#E040FB` | Master transport, playback pacing, and sequencer start. |
| **Key 4** | **Modifier `SHIFT` (Layer Fn)** | **Royal Purple / Violet**| `#7C4DFF` | Status modifier. Signals access to secondary functions. |
| **Keys 1, 3, 10** | **Hidden / Disabled Switches** | **LED Disabled (OFF)** | `#000000` | Extinguished to prevent internal chassis light leakage. |

### 4.2 Layer-Dependent Lighting Behaviors
In the SayoDevice web configurator (`Lighting` tab):
1. **Layer 0 (Default Mode)**:
   - Configure **Static Cluster Colors** as detailed above.
   - Lighting effect: **Static** or **Reactive Pulse** (keys briefly brighten to white on touch).
2. **Layer 1 (Shift Active)**:
   - Configure the lighting mode for Layer 1 so that all keys switch to a unified **Deep Amber / Orange (`#FF6D00`)** or **Blinking Purple**.
   - Provides immediate visual feedback that shifted commands (Snapshot switching, Panic, Mixer jump, Recording) are primed!

---

## 5. Zynthian UI Integration & CUIA Keybindings

Zynthian OS provides a dedicated subsystem for binding USB HID keyboards directly to Callable UI Actions (CUIA).

### 5.1 Configuring Keybindings via Zynthian Webconf
1. Connect to Zynthian Webconf: `https://zynthian.local` (default credentials: `raspberry` / `opensynth`).
2. In the top menu, navigate to **INTERFACE** $\rightarrow$ **UI Keybindings**.
3. Under **Key Actions**, verify or map the incoming keycodes:

```text
Key: Up          ---> Action: ARROW_UP
Key: Down        ---> Action: ARROW_DOWN
Key: Left        ---> Action: ARROW_LEFT
Key: Right       ---> Action: ARROW_RIGHT
Key: Return      ---> Action: SELECT
Key: Escape      ---> Action: BACK
Key: Tab         ---> Action: SWITCH_CHAIN
Key: Space       ---> Action: TOGGLE_PLAY
Key: Page_Up     ---> Action: PAGE_UP
Key: Page_Down   ---> Action: PAGE_DOWN
Key: bracketleft ---> Action: PREV_SNAPSHOT
Key: bracketright---> Action: NEXT_SNAPSHOT
Key: F2          ---> Action: SCREEN_MIXER
```

4. Click **Save**. The keybindings take effect immediately across all Zynthian screens without requiring a reboot.

### 5.2 Autonomous "No-Touchscreen" Workflow Examples

#### Example 1: Creating a New Synth Chain & Loading a Preset
1. Press **`A`** (`Return`) on the main dashboard to open the Main Menu.
2. Use **`DOWN`** to navigate to `New Synth Track` and press **`A`**.
3. Use **`UP` / `DOWN`** to select the engine (e.g., `Dexed`, `OB-Xd`, `Surge XT`) and press **`A`**.
4. Use **`UP` / `DOWN`** to scroll through sound categories and presets. Press **`A`** to load the instrument.
5. Press **`B`** (`Escape`) to back out to the main performance view.
6. Press **`START`** (`Space`) to start the sequencer!

#### Example 2: Emergency Panic & Mixer Adjustment During Live Performance
1. A MIDI feedback loop causes stuck notes on an external synthesizer:
   - Press **`SHIFT` + `B`** (`MIDI Panic`). Zynthian immediately broadcasts All Notes Off across all chains.
2. Need to adjust track balances:
   - Press **`SHIFT` + `SELECT`** to instantly pull up the Zynmixer screen.
   - Use **`LEFT` / `RIGHT`** to select the desired track channel.
   - Use **`UP` / `DOWN`** to adjust the volume fader.
   - Press **`B`** to return to instrument control.

---

## 6. Linux Diagnostics & Troubleshooting

### 6.1 Diagnostic Commands Quick-Reference

When diagnosing macro keyboard connection or key transmission issues over SSH:

```bash
# 1. Verify USB enumeration and Vendor/Product ID
lsusb

# Expected output contains SayoDevice or composite HID descriptor:
# Bus 001 Device 005: ID 8089:0004 SayoDevice USB Keyboard

# 2. Inspect kernel input device registration
dmesg | grep -i "input" | tail -n 20

# 3. Test real-time keypress events using evtest
evtest
# (Select the SayoDevice keyboard event node, e.g., /dev/input/event3, then press keys to observe scan codes)
```

### 6.2 Common Troubleshooting Scenarios

#### Problem 1: WebHID Cannot Detect Device on `sayodevice.com`
- **Symptom**: Clicking "Connect" shows an empty device list or "No compatible devices found".
- **Root Cause**: Non-Chromium browser used, or another application holds an exclusive lock on the USB device.
- **Solution**:
  1. Open the page exclusively in Google Chrome, Brave, or Microsoft Edge.
  2. Disconnect any local desktop configuration utilities or games (like *osu!*).
  3. Under Linux desktop, create a udev rule to allow non-root WebHID access:
     ```bash
     echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="8089", MODE="0666"' | sudo tee /etc/udev/rules.d/99-sayodevice.rules
     sudo udevadm control --reload-rules && sudo udevadm trigger
     ```

#### Problem 2: Arrow Keys Jump Irregularly or Double-Trigger
- **Symptom**: Pressing `DOWN` skips multiple items in Zynthian listboxes.
- **Root Cause**: Key debounce time is set too low ($< 5\text{ ms}$) in the SayoDevice configuration, or key repeat rate in Linux is excessively fast.
- **Solution**: In `sayodevice.com`, increase the key debounce filter to **$15\text{ ms} - 25\text{ ms}$**.

#### Problem 3: `SHIFT` Key Does Not Switch Layers
- **Symptom**: Holding `SHIFT` and pressing `UP` still sends standard `Up Arrow` instead of `Page Up`.
- **Root Cause**: Physical button is mapped to standard keyboard `Shift` (`Left Shift`) instead of SayoDevice's **`Layer Switch / Fn`** action.
- **Solution**: In `sayodevice.com`, change the Key Type of physical Key 9 from "Normal Key" to **"Layer Function"** $\rightarrow$ **"Momentary Layer 1"**.

---

## 7. Technical Authority & Reference Links

1. **SayoDevice Official Resources**:
   - [SayoDevice WebHID App](https://sayodevice.com/)
   - [SayoDevice Documentation Manual](https://manual.sayodevice.com/#/en/docs/std/web_hid/README)
   - [SayoDevice GitHub Repository](https://github.com/Sayobot/SayoDevice_manual)
2. **mc-zynthian Project Documentation & Ecosystem**:
   - Master Roadmap & Architecture: [`README.md`](../README.md)
   - Pisound Installation & Configuration Bible: [`docs/pisound-guide.md`](pisound-guide.md)
   - Ableton Push 1 Hardware Guide: [`docs/push-guide.md`](push-guide.md)
   - Ableton Push 1 Technical Protocols: [`docs/push-protocols.md`](push-protocols.md)
   - Korg nanoKONTROL Guide: [`docs/nanokontrol-guide.md`](nanokontrol-guide.md)
   - Roland MC-101 Operational Reference: [`docs/mc101-guide.md`](mc101-guide.md)
   - Roland MC-101 SysEx & Memory Architecture: [`docs/mc101-sysex.md`](mc101-sysex.md)

