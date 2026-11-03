# SayoDevice 2x6F RGB Macro Keyboard: Zynthian Controller Guide & Reference Manual

Comprehensive technical specification, web configuration guide, and Zynthian integration manual for the **SayoDevice 2x6F RGB 12-Key USB Macro Keyboard** (customized in a 9-key retro game controller layout).

This document serves as the foundational guide for Stage 1 of the [`mc-zynthian`](../README.md) project, fulfilling the core architectural requirement: **enabling full autonomous navigation of the Zynthian UI via tactile physical controls, making the touchscreen an optional assist**. For full hardware specifications, bill of materials, and enclosure assembly, see [`docs/rpi-specs.md`](rpi-specs.md) and [`assets/case-assembly.stl`](../assets/case-assembly.stl).

---

## 1. Hardware Architecture & Physical Matrix Layout

The macro controller is based on the **SayoDevice 2x6F RGB 12-Key programmable USB keypad** (Sayobot / WebHID ecosystem). 

The underlying circuit board contains a **$2 \times 6$ matrix (2 rows of 6 keys)** of 12 mechanical key switches with individual per-key RGB backlighting. The custom physical enclosure deliberately exposes **9 functional keys** by masking/disabling 3 keys (Keys 1, 3, and 10), creating a classic retro game console layout with a cross D-pad on the left and action/system buttons on the right:

```
+---------------------------------------------------------------------------------------------------------------------------------------+
|  [ Key 1: HIDDEN ]   [ Key 2: UP ]       [ Key 3: HIDDEN ]   [ Key 4: Fn ]          [ Key 5: A ]            [ Key 6: B ]              | (Row 1)
|  (Internal/Masked)   (D-Pad Up)          (Internal/Masked)   (Hold for Layer 1)     (Action A / Select)     (Action B / Back)         |
|                                                                                                                                       |
|  [ Key 7: LEFT ]     [ Key 8: DOWN ]     [ Key 9: RIGHT ]    [ Key 10: HIDDEN ]     [ Key 11: C ]           [ Key 12: D ]             | (Row 2)
|  (D-Pad Left)        (D-Pad Down)        (D-Pad Right)       (Internal/Masked)      (Switch Chain)          (Transport Play/Stop)     |
+---------------------------------------------------------------------------------------------------------------------------------------+
| <----------------- LEFT CLUSTER: CROSS D-PAD -----------------> | <------------------ RIGHT CLUSTER: RETRO CONSOLE -----------------> |
```

### 1.1 Complete 12-Key ($2 \times 6$) Hardware Matrix Breakdown

Numbering from **Left to Right across Row 1, then Left to Right across Row 2**:

#### Row 1 (Keys 1 through 6)
| Key # | Position | Hardware Status | Physical Cluster | Primary Role |
|---|---|---|---|---|
| **Key 1** | Row 1, Col 1 | **Hidden / Masked** | Top-Left Corner | Unexposed / Disabled |
| **Key 2** | Row 1, Col 2 | **Exposed** | D-Pad Top | Directional Up |
| **Key 3** | Row 1, Col 3 | **Hidden / Masked** | Top-Right Corner | Unexposed / Disabled |
| **Key 4** | Row 1, Col 4 | **Exposed** | Center Modifier | Layer Switch (`Fn`) |
| **Key 5** | Row 1, Col 5 | **Exposed** | Action Cluster | Primary Action A |
| **Key 6** | Row 1, Col 6 | **Exposed** | Action Cluster | Secondary Action B |

#### Row 2 (Keys 7 through 12)
| Key # | Position | Hardware Status | Physical Cluster | Primary Role |
|---|---|---|---|---|
| **Key 7** | Row 2, Col 1 | **Exposed** | D-Pad Left | Directional Left |
| **Key 8** | Row 2, Col 2 | **Exposed** | D-Pad Bottom | Directional Down |
| **Key 9** | Row 2, Col 3 | **Exposed** | D-Pad Right | Directional Right |
| **Key 10**| Row 2, Col 4 | **Hidden / Masked** | Bottom-Center | Unexposed / Disabled |
| **Key 11**| Row 2, Col 5 | **Exposed** | Action Cluster | Tertiary Action C |
| **Key 12**| Row 2, Col 6 | **Exposed** | Action Cluster | Quaternary Action D |

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
- **Modern WebHID Configuration App**: [app.sayodevice.com](https://app.sayodevice.com/)
- **Legacy WebHID Portal (for initial connection & firmware update)**: [old.sayodevice.com/device](https://old.sayodevice.com/device)
- **Official Documentation**: [SayoDevice WebHID Documentation](https://manual.sayodevice.com/#/en/docs/std/web_hid/README)
- **Source Repository & Firmware**: [Sayobot/SayoDevice_manual GitHub](https://github.com/Sayobot/SayoDevice_manual)

### 2.2 System & Linux Mint Permissions Setup
> [!IMPORTANT]
> **Browser Compatibility & Linux udev Rule:**
> The SayoDevice configurator utilizes the **WebHID API**, which allows direct low-level USB communication from the browser without installing desktop software.
> - **Supported Browsers**: Google Chrome, Microsoft Edge, Brave, Opera, or any modern Chromium-based browser (Firefox and Safari do not support WebHID).
> - **Linux Mint / Ubuntu Permissions**: Under Linux, raw USB HID interfaces (`/dev/hidraw*`) require root permissions by default. When clicking "Connect" in Chrome, the browser fails silently unless a udev rule is applied:
>   ```bash
>   echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666"' | sudo tee /etc/udev/rules.d/99-sayodevice.rules
>   sudo udevadm control --reload-rules && sudo udevadm trigger
>   ```
>   After running these commands, unplug and reconnect the keypad's USB cable.

### 2.3 Step-by-Step Programming Walkthrough

```
+---------------------------------------------------------------------------------------------------+
| 1. Connect Device  ---> 2. Apply Linux udev  ---> 3. Upgrade Firmware  ---> 4. Map Keys/Layers    |
|    (Linux Mint PC)         (/dev/hidraw*)            (old.sayodevice)          (app.sayodevice)   |
|                                                                                     |             |
| 6. Deploy to Pi    <--- 5. Save to EEPROM    <--------------------------------------+             |
+---------------------------------------------------------------------------------------------------+
```

1. **Connect to Programming Machine**:
   - Plug the SayoDevice 2x6F RGB into your Linux workstation using a USB data cable.
2. **Initial Firmware Upgrade**:
   - If using stock firmware, open `https://old.sayodevice.com/device` in Google Chrome and upgrade the device firmware.
3. **Open Modern Configurator**:
   - Navigate to `https://app.sayodevice.com/` and connect to the SayoDevice 2x6F RGB.
4. **Configure Key Codes & Layers**:
   - Map **Layer 0** (Default) and **Layer 1** (Shifted / Fn held) as detailed in Section 3.
5. **Commit Configuration to Hardware**:
   - Click **Save** / **Write to Device**. The mappings are committed to internal non-volatile EEPROM.
   - Disconnect the keyboard. The device is now permanently configured and ready for Zynthian!

---

## 3. Layer Architecture & Keystroke Generation

The SayoDevice 2x6F RGB operates as a hardware-level USB HID keyboard encoder with internal multi-layer mapping capabilities:

### 3.1 Hardware Layer Modes
- **Layer 0 (Base Layer):** The default operational layer active when no modifier key is engaged. Every key sends its assigned primary standard HID scan code.
- **Layer 1 (Secondary Layer):** Activated via a dedicated modifier key. In the web configurator, any physical switch can be designated as a **Layer Switch (`Fn`)**:
  - **Momentary (Press & Hold):** Layer 1 is only active while the modifier key is held down; releasing it immediately returns the keypad to Layer 0.
  - **Toggle (Latch):** Pressing the modifier toggles between Layer 0 and Layer 1.
- **EEPROM Storage:** All layer assignments are written directly to internal flash memory. The device requires no host background software or drivers; when plugged into any host OS (Linux, macOS, Windows), it enumerates as a standard USB composite keyboard.

### 3.2 Keystroke Emission & HID Protocol
- **Standard Scan Codes:** Keys can emit standard alphanumeric ASCII keys (`A`–`Z`, `0`–`9`), directional arrows (`Up`, `Down`, `Left`, `Right`), navigation keys (`Enter`, `Escape`, `Space`, `Tab`, `Page Up`, `Page Down`), or function keys (`F1`–`F12`).
- **Compound Modifiers:** Keys can optionally emit combination strokes (e.g., `Ctrl+C`, `Shift+Tab`, `Alt+F4`).
- **Disabled Keys:** Unexposed or unused keys can be assigned to `none` (No Key) to ensure no spurious events are generated.

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

## 5. Linux Diagnostics & Troubleshooting

### 5.1 Diagnostic Commands Quick-Reference

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

### 5.2 Common Troubleshooting Scenarios

#### Problem 1: WebHID Cannot Detect Device on `sayodevice.com`
- **Symptom**: Clicking "Connect" shows an empty device list or "No compatible devices found".
- **Root Cause**: Non-Chromium browser used, or raw HID device permissions restricted in Linux.
- **Solution**:
  1. Open the page exclusively in Google Chrome, Brave, or Microsoft Edge.
  2. Under Linux desktop, create a udev rule to allow non-root WebHID access:
     ```bash
     echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666"' | sudo tee /etc/udev/rules.d/99-sayodevice.rules
     sudo udevadm control --reload-rules && sudo udevadm trigger
     ```
  3. Reconnect the USB cable.

#### Problem 2: Arrow Keys Jump Irregularly or Double-Trigger
- **Symptom**: Pressing keys skips multiple items in software lists.
- **Root Cause**: Key debounce time is set too low ($< 5\text{ ms}$) in the SayoDevice configuration, or key repeat rate in Linux is excessively fast.
- **Solution**: In `app.sayodevice.com`, increase the key debounce filter to **$15\text{ ms} - 25\text{ ms}$**.

#### Problem 3: `Fn` Key Does Not Switch Layers
- **Symptom**: Holding `Fn` still sends standard Layer 0 keycodes.
- **Root Cause**: Physical button is mapped to standard keyboard modifier (`Left Shift` or `Alt`) instead of SayoDevice's **`Layer Switch / Fn`** action.
- **Solution**: In `app.sayodevice.com`, set the Key Type of physical Key 4 to **"Layer Function"** $\rightarrow$ **"Momentary Layer 1"**.

---

## 6. Technical Authority & Reference Links

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

