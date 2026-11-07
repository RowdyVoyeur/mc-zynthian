# SayoDevice 2x6F RGB Macro Keyboard: Technical Specification & Configuration Manual

Comprehensive technical reference, hardware specifications, WebHID configuration manual, and Linux integration guide for the **SayoDevice 2x6F RGB 12-Key USB Mechanical Keypad** (Sayobot WebHID ecosystem).

This document provides factual, verified engineering specifications and operational procedures for the macro controller hardware. For the specific key mappings, layer assignments, and Zynthian UI keybindings utilized in this build, see the project build log in [`README.md`](../README.md).

---

## 1. Hardware Architecture & Specifications

The SayoDevice 2x6F RGB is a class-compliant programmable USB Human Interface Device (HID) based on a 12-switch mechanical key matrix.

```
+-------------------------------------------------------------------------------------------------------+
|  [ Key 1 ] (Col 1)    [ Key 2 ] (Col 2)    [ Key 3 ] (Col 3)    [ Key 4 ] (Col 4)    [ Key 5 ] (Col 5)    [ Key 6 ] (Col 6)   | (Row 1)
|                                                                                                       |
|  [ Key 7 ] (Col 1)    [ Key 8 ] (Col 2)    [ Key 9 ] (Col 3)    [ Key 10] (Col 4)    [ Key 11] (Col 5)    [ Key 12] (Col 6)   | (Row 2)
+-------------------------------------------------------------------------------------------------------+
```

### 1.1 Complete 12-Key ($2 \times 6$) Hardware Matrix

Numbering proceeds from left to right across Row 1 (Keys 1–6), then left to right across Row 2 (Keys 7–12):

| Physical Key | Matrix Position | Hardware Attributes | Default HID Functionality |
|---|---|---|---|
| **Key 1** | Row 1, Column 1 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 2** | Row 1, Column 2 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 3** | Row 1, Column 3 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 4** | Row 1, Column 4 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 5** | Row 1, Column 5 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 6** | Row 1, Column 6 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 7** | Row 2, Column 1 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 8** | Row 2, Column 2 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 9** | Row 2, Column 3 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 10**| Row 2, Column 4 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 11**| Row 2, Column 5 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |
| **Key 12**| Row 2, Column 6 | Mechanical switch with per-key RGB LED | Fully programmable to any HID scan code, modifier, or layer function |

### 1.2 Electrical & Microcontroller Specifications
- **Host Interface:** USB 2.0 Full-Speed (12 Mbps), class-compliant USB composite HID keyboard.
- **Connector Type:** USB Type-C or Micro-B (dependent on production revision).
- **Power Supply:** $5\text{ V DC}$ standard USB bus-powered, nominal operating draw $< 80\text{ mA}$ (fully compliant with Raspberry Pi 4 USB 2.0/3.0 port power delivery).
- **Onboard Microcontroller:** High-speed embedded USB MCU (CH55x or RP2040 architecture) with integrated non-volatile EEPROM/Flash storage.
- **Zero-Driver Operation:** Once configuration is written to internal memory, the keyboard requires no resident background software, daemons, or vendor drivers. It functions as a standard hardware keyboard across Linux, Windows, macOS, and embedded operating systems.
- **Switch Sockets:** Hot-swappable mechanical switch sockets (standard Cherry MX footprint).
- **Per-Key RGB Lighting:** 12 individually addressable surface-mount RGB LEDs soldered directly beneath each switch location.

---

## 2. Firmware Architecture & Capabilities

### 2.1 Keystroke Generation & Modifiers
Each physical switch can be mapped to:
1. **Standard HID Keycodes:**
   - Alphanumeric characters (`A`–`Z`, `0`–`9`).
   - Directional navigation keys (`Up`, `Down`, `Left`, `Right`).
   - Standard control keys (`Enter`, `Escape`, `Space`, `Tab`, `Backspace`, `Delete`).
   - Page navigation (`Page Up`, `Page Down`, `Home`, `End`).
   - Function keys (`F1`–`F24`).
2. **Compound Modifiers:** Any key can send combinations of modifier keys (`Ctrl`, `Shift`, `Alt`, `GUI/Super`) alongside a base keycode (e.g., `Ctrl+C`, `Shift+Tab`).
3. **Disabled State (`none`):** Unused switches can be explicitly disabled so physical presses emit no USB HID report.

### 2.2 Layer Engine & Switching Mechanics
The onboard firmware supports multi-layer mapping (up to 16 independent layers in memory):
- **Momentary (Hold):** A switch acts as a temporary modifier (`Fn`). While held, the designated secondary layer is active; releasing it returns immediately to the base layer.
- **Toggle (Latch):** Pressing the switch switches between Layer $A$ and Layer $B$.
- **Cyclical Layer Switching:** A switch can be assigned to advance to the next layer sequentially ($0 \to 1 \to 2 \to \dots \to 0$). This allows single-key navigation across multiple functional banks without requiring dual-key chord combinations.

### 2.3 RGB Backlighting Engine
The lighting controller operates per-key and per-layer:
- **Modes:** Static color, slow breathing / pulsating (with user-defined cycle period), reactive pulse (illuminates upon keydown), or completely disabled (`#000000` / OFF).
- **Status Indicator Function:** Because lighting is tied to the active layer, individual keys can be configured as visual indicators (e.g., extinguished on Layer 0, breathing in specific colors on secondary layers) to signal the active operational bank to the user without requiring an on-screen display.

---

## 3. WebHID Configuration Workflow

The SayoDevice contains no onboard screen or hardware DIP switches. All configuration is performed through the browser using the WebHID API and committed directly to the microcontroller's internal EEPROM.

### 3.1 Portal Links & Browser Requirements
- **Modern Configurator:** [app.sayodevice.com](https://app.sayodevice.com/)
- **Legacy Configurator (Firmware Recovery):** [old.sayodevice.com/device](https://old.sayodevice.com/device)
- **Official Documentation:** [SayoDevice WebHID Documentation](https://manual.sayodevice.com/#/en/docs/std/web_hid/README)
- **Browser Compatibility:** **Chromium-based browsers only** (Google Chrome, Brave, Microsoft Edge, Opera). The WebHID API is not implemented in Firefox or Safari.

### 3.2 Step-by-Step Programming Walkthrough

```
+---------------------------------------------------------------------------------------------------+
| 1. Connect Device  ---> 2. Apply Linux udev  ---> 3. Upgrade Firmware  ---> 4. Map Keys/Layers    |
|    (Linux PC)              (/dev/hidraw*)            (old.sayodevice)          (app.sayodevice)   |
|                                                                                     |             |
| 6. Deploy to Host  <--- 5. Write to EEPROM   <--------------------------------------+             |
+---------------------------------------------------------------------------------------------------+
```

1. **Connect Device:** Connect the keypad to a programming computer via USB data cable.
2. **Apply Linux udev Rule (if configuring under Linux):** Ensure user-space WebHID access is permitted (see Section 4).
3. **Firmware Verification / Initial Update:** If connecting a factory-fresh unit for the first time, navigate to `https://old.sayodevice.com/device` in Google Chrome to verify and flash the latest firmware.
4. **Configure in Modern Portal:** Navigate to `https://app.sayodevice.com/`, select the detected device, and configure keycodes, layers, debounce times, and RGB lighting.
5. **Write to EEPROM:** Click **Save** / **Write to Device**. The configuration is permanently burned to onboard flash memory.
6. **Disconnect:** The keypad can now be disconnected and plugged into the target host system; all settings remain intact without software dependencies.

---

## 4. Verified Linux Integration & Troubleshooting

### 4.1 Challenge: Device Not Detected via WebHID in Linux
- **Symptom:** In Google Chrome, clicking "Connect" on `app.sayodevice.com` displays "No compatible devices found" or fails silently, even though the device appears in `lsusb`.
- **Root Cause:** Modern Linux distributions enforce strict default permissions on raw USB HID devices (`/dev/hidraw*`), restricting access exclusively to `root`. WebHID requires user-level read/write permissions to establish a control transfer channel.
- **Verified Solution:** Create a persistent udev rule granting read/write permissions to raw HID interfaces:
  ```bash
  echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666"' | sudo tee /etc/udev/rules.d/99-sayodevice.rules
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```
  Unplug and reconnect the keypad's USB cable. Chrome will now immediately detect the device upon clicking "Connect".

### 4.2 Challenge: Modern Configurator Connection Errors
- **Symptom:** Chrome recognizes the USB device, but `app.sayodevice.com` reports communication timeouts or protocol parse errors.
- **Root Cause:** Units running older factory firmware lack the handshake structures required by the modern WebHID portal.
- **Verified Solution:** Open `https://old.sayodevice.com/device` first, perform the firmware update through the legacy interface, and then return to `https://app.sayodevice.com/`.

### 4.3 Challenge: Key Bouncing & Spurious Double-Triggers
- **Symptom:** A single physical keypress registers multiple times in the host operating system or skips menu entries.
- **Root Cause:** Mechanical contact bounce occurring faster than the microcontroller's default debounce threshold.
- **Verified Solution:** In `app.sayodevice.com`, increase the key debounce filter setting to **$15\text{ ms} - 25\text{ ms}$** before saving to EEPROM.

---

## 5. Linux Host Diagnostic Commands

To verify USB enumeration, driver binding, and real-time keystroke transmission on Linux without desktop tools:

```bash
# 1. Verify USB enumeration and Vendor/Product ID
lsusb

# Expected output contains SayoDevice composite descriptor:
# Bus 001 Device 005: ID 8089:0004 SayoDevice USB Keyboard

# 2. Inspect kernel HID driver binding
dmesg | grep -i "input" | tail -n 20

# 3. Test real-time scan code generation
evtest
# Select the SayoDevice event node (e.g., /dev/input/event3) and press switches
# to verify clean, non-bouncing make/break keystroke reports.
```

---

## 6. Technical Authority & Reference Links

1. **SayoDevice Resources:**
   - WebHID Configuration App: [app.sayodevice.com](https://app.sayodevice.com/)
   - Legacy WebHID Interface: [old.sayodevice.com/device](https://old.sayodevice.com/device)
   - Official Manual: [SayoDevice WebHID Documentation](https://manual.sayodevice.com/#/en/docs/std/web_hid/README)
   - Source Repository: [Sayobot/SayoDevice_manual GitHub](https://github.com/Sayobot/SayoDevice_manual)
2. **Project Documentation:**
   - Master Build Roadmap & Verified Configuration: [`README.md`](../README.md)
   - Hardware Specifications & Assembly: [`docs/rpi-specs.md`](rpi-specs.md)
   - Zynthian OS Architecture & CUIA Reference: [`docs/zynthian-guide.md`](zynthian-guide.md)
