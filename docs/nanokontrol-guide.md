# Korg nanoKONTROL (Version 1): Hardware Architecture, MIDI & SysEx Specification Bible

Comprehensive operational manual, technical hardware reference, and System Exclusive (SysEx) implementation specification for the original **Korg nanoKONTROL** (Version 1, model year 2008).

This document serves as the foundation for developing companion tools, headless Python configuration scripts, and native Zynthian control integrations for Stage 2 of the [`mc-zynthian`](../README.md) project.

> [!IMPORTANT]
> **Strict Hardware Scope — nanoKONTROL Version 1 Only:**
> This document pertains **exclusively** to the original first-generation **Korg nanoKONTROL (v1)** featuring **9 channel strips, 9 knobs, 9 faders, 18 assignable buttons, 6 transport buttons, and 4 onboard hardware scenes**.
> It does **not** cover the nanoKONTROL2 (which reduced channel strips to 8 and eliminated internal scenes) or the nanoKONTROL Studio (Bluetooth/jogwheel model). All physical layouts, memory offsets, and SysEx formats documented here are strictly specific to Version 1.

---

## 1. Physical Hardware Overview & Surface Architecture

The Korg nanoKONTROL is a slim-line, ultra-portable USB-MIDI control surface designed to provide dense tactile mixing, instrument parameter editing, and transport control.

```
+---------------------------------------------------------------------------------------------------+
|  [REW]  [PLAY]  [FF]   [LOOP]  [STOP]  [REC]     (Knob 1) (Knob 2) (Knob 3) ... (Knob 8) (Knob 9) |
|                                                                                                   |
|  [SCENE]                                         [Btn A1] [Btn A2] [Btn A3] ... [Btn A8] [Btn A9] |
|  (1) (2) (3) (4) Scene LEDs                      [Btn B1] [Btn B2] [Btn B3] ... [Btn B8] [Btn B9] |
|                                                                                                   |
|  [KORG LOGO]                                     | || |   | || |   | || |       | || |   | || |   |
|  [USB Mini-B]                                    | || |   | || |   | || |  ...  | || |   | || |   |
|                                                  (Fdr 1)  (Fdr 2)  (Fdr 3)      (Fdr 8)  (Fdr 9)  |
|                                                   Strip 1  Strip 2  Strip 3      Strip 8  Strip 9 |
+---------------------------------------------------------------------------------------------------+
```

### 1.1 Physical Dimensions & Electrical Specifications
- **Form Factor**: Ultra-compact slim-line controller.
- **Dimensions**: $320\text{ mm (W)} \times 82\text{ mm (D)} \times 29.5\text{ mm (H)}$ ($12.60" \times 3.23" \times 1.16"$).
- **Weight**: $290\text{ g}$ ($10.23\text{ oz}$).
- **Power Supply**: Standard $5\text{V}$ USB bus powered via USB Mini-B socket.
- **Current Consumption**: Less than $100\text{ mA}$ (fully operable from unpowered USB hubs and Raspberry Pi USB ports).
- **USB Device Identity**:
  - Class-compliant USB MIDI 1.0 device (no vendor drivers required on Linux/Zynthian).
  - USB Vendor ID (`idVendor`): `0x0944` (KORG, Inc.).
  - USB Product ID (`idProduct`): `0x0104` (nanoKONTROL v1).
  - ALSA Client Name: `nanoKONTROL` or `nanoKONTROL MIDI 1`.

### 1.2 Surface Control Inventory
1. **9 MIDI Control Groups (Strips 1 through 9)**:
   - **9 Rotary Knobs**: Smooth $270^\circ$ potentiometers sending $7\text{-bit}$ continuous data ($0..127$).
   - **9 Linear Sliders (Faders)**: $30\text{ mm}$ travel linear potentiometers ($0..127$).
   - **9 Upper Buttons ("Button 1" / "Switch A")**: Momentary or latching tactile rubber buttons with integrated red status LEDs.
   - **9 Lower Buttons ("Button 2" / "Switch B")**: Momentary or latching tactile rubber buttons with integrated red status LEDs.
2. **6 Dedicated Transport Buttons**:
   - `[REW]` (Rewind), `[PLAY]`, `[FF]` (Fast Forward), `[LOOP]`, `[STOP]`, and `[REC]`.
   - Each button features a tactile micro-switch with an integrated red LED indicator.
3. **1 Dedicated `[SCENE]` Button**:
   - Cycles through the 4 internal hardware memory scenes.
4. **4 Scene Indicator LEDs**:
   - Red LEDs labeled **1, 2, 3, 4** indicating which memory scene is currently active in hardware.

### 1.3 The 4 Hardware Scenes: $36$ Channel Strips in One Device
Unlike simple single-map controllers, nanoKONTROL v1 contains an internal EEPROM storing **4 independent Scene configurations**:
- Pressing `[SCENE]` on the physical hardware instantly switches all control assignments across the device without requiring computer intervention.
- The 4 scenes effectively yield:
  - **36 Sliders** ($9 \times 4$)
  - **36 Rotary Knobs** ($9 \times 4$)
  - **72 Channel Buttons** ($18 \times 4$)
  - **24 Transport Button Mappings** ($6 \times 4$)

---

## 2. Key Features & Operational Mechanics

### 2.1 The 9 MIDI Control Groups
Each vertical control strip is treated as an independent group containing:
1. **Knob**: Can be enabled/disabled, assigned to any MIDI CC ($0..127$), and assigned custom **Left Value** (minimum) and **Right Value** (maximum).
2. **Slider**: Can be enabled/disabled, assigned to any MIDI CC ($0..127$), and assigned custom **Lower Value** (minimum) and **Upper Value** (maximum).
3. **Button 1 (Upper) & Button 2 (Lower)**: Each button can be configured independently:
   - **Assign Type**: `No Assign`, `Control Change` (CC), or `MIDI Note`.
   - **Behavior**: `Momentary` or `Toggle`.
   - **On Value**: Transmitted when pressed ($0..127$). In Note mode, this sets the Note-On **Velocity** ($1..127$).
   - **Off Value**: Transmitted when released in CC mode ($0..127$).
   - **Attack Time ($0..127$) & Release Time ($0..127$)**: Unique parameter slewing (see Section 2.3).

### 2.2 Transport Buttons: CC vs. MMC Mode
The 6 transport buttons (`REW`, `PLAY`, `FF`, `LOOP`, `STOP`, `REC`) can transmit either:
1. **Control Change (CC)**: Standard MIDI CC numbers ($0..127$) with `Momentary` (press = $127$, release = $0$) or `Toggle` ($127$ / $0$ alternate) behavior.
2. **MIDI Machine Control (MMC)**: Sends standard realtime SysEx machine control commands (`01H` Stop, `02H` Play, `06H` Record, etc.) with a configurable MMC Device ID ($0..127$, default $127 = \text{All-Call}$).

### 2.3 Unique Hardware Slew Ramping: Attack & Release Times
A rare and powerful feature exclusive to the nanoKONTROL v1 is **hardware-level parameter slewing** for buttons assigned to Control Change:

```
CC Value
  ^
  |                  +---------------------+ (On Value)
  |                 /                       \
  |                /                         \
  |               /                           \
  |              /                             \
  +-------------+                               +------------> Time
    (Off Value) |<- Attack Time ->|             |<- Release Time ->|
                Button Pressed                  Button Released
```

- **Attack Time ($0..127$)**: Sets the transition time required for the transmitted CC value to ramp smoothly from **Off Value** up to **On Value** after the button is pressed.
- **Release Time ($0..127$)**: Sets the transition time required for the transmitted CC value to decay smoothly from **On Value** back down to **Off Value** after the button is released.
- **Application**: Allows soft swelling of filter cutoffs, gradual volume dips, or smooth pitch sweeps directly from a tactile button press without requiring host DAW envelope generation.

### 2.4 Control Value Inversion & Bounding
Both knobs and sliders support arbitrary minimum and maximum boundaries:
- **Inverted Polarity**: Setting Lower Value = $127$ and Upper Value = $0$ inverts the fader travel (pulling downward increases parameter values; pushing upward decreases them).
- **Restricted Range**: Setting Lower Value = $40$ and Upper Value = $90$ prevents a fader or knob from driving synth filters into distortion or inaudible sub-bass.

### 2.5 Restoring Factory Default Settings
If controller mappings become corrupted or need to be reset to factory condition:
1. Disconnect the USB cable from the nanoKONTROL.
2. Press and hold down **`[REC]` + `[STOP]` + `[SCENE]`** simultaneously.
3. While holding all three buttons, plug the USB cable into the computer or Zynthian.
4. The Scene LEDs will illuminate, and the internal EEPROM will be restored to factory default mappings. The initialization takes several seconds; **do not disconnect the cable during this process**.

---

## 3. Complete MIDI Implementation Specification

### 3.1 Transmitted Channel Messages

| Message Type | Status Byte (Hex) | Data Byte 1 | Data Byte 2 | Originating Physical Controls |
|---|---|---|---|---|
| **Note Off** | `0x8n` | Note Number $kk$ ($0..127$) | Fixed Velocity `0x40` ($64$) | Button 1 / Button 2 (when Assign Type = Note) |
| **Note On** | `0x9n` | Note Number $kk$ ($0..127$) | Velocity $VV$ ($1..127$) | Button 1 / Button 2 (Velocity determined by On Value) |
| **Control Change** | `0xBn` | CC Number $cc$ ($0..127$) | Value $vv$ ($0..127$) | Knobs, Sliders, Buttons 1 & 2 (CC Mode), Transport |

*Where $n$ is the MIDI Channel ($0..15$, representing Channels 1 through 16).*

### 3.2 Universal System Exclusive Messages

#### 1. Universal Non-Realtime: Device Inquiry
Host sends:
```text
F0 7E gg 06 01 F7
```
*(Where $gg = \text{Global Channel } 00\text{..}0F$, or $7F = \text{Any Channel}$).*

nanoKONTROL replies:
```text
F0 7E 0g 06 02 42 04 01 00 00 xx xx xx xx F7
```
- `F0 7E`: Universal Non-Realtime SysEx Header
- `0g`: Global MIDI Channel ($g = 0..F$)
- `06 02`: General Information — Device Identity Reply
- `42`: KORG Manufacturer ID
- `04 01`: Family ID (`0x0104`, nanoKONTROL Family)
- `00 00`: Member ID (`0x0000`, nanoKONTROL v1)
- `xx xx`: Minor Firmware Version (LSB, MSB)
- `xx xx`: Major Firmware Version (LSB, MSB)
- `F7`: End of Exclusive (EOX)

#### 2. Universal Realtime: MIDI Machine Control (MMC)
When transport buttons are configured for MMC, pressing a button transmits:
```text
F0 7F dd 06 cc F7
```
- `F0 7F`: Universal Realtime SysEx Header
- `dd`: MMC Device ID ($00..7E$, or $7F = \text{All-Call}$)
- `06`: Machine Control Command code
- `cc`: MMC Command byte:

| MMC Command Byte | Command Name | Default Transport Button |
|---|---|---|
| **`01H`** | **Stop** | `[STOP]` |
| **`02H`** | **Play** | `[PLAY]` |
| **`03H`** | **Deferred Play** | Assignable |
| **`04H`** | **Fast Forward** | `[FF]` |
| **`05H`** | **Rewind** | `[REW]` |
| **`06H`** | **Record Strobe** | `[REC]` |
| **`07H`** | **Record Exit** | Assignable |
| **`08H`** | **Record Pause** | Assignable |
| **`09H`** | **Pause** | Assignable |
| **`0AH`** | **Eject** | Assignable |
| **`0BH`** | **Chase** | Assignable |
| **`0CH`** | **Command Error Reset** | Assignable |
| **`0DH`** | **MMC Reset** | Assignable |

---

## 4. Korg Proprietary System Exclusive (SysEx) Protocol

The nanoKONTROL uses Korg's proprietary SysEx framing to inspect hardware ports, request full scene data dumps, flash edited scenes into EEPROM, and remotely switch active scenes.

### 4.1 Master SysEx Framing Structure
All Korg proprietary messages follow this byte structure:

$$\begin{aligned}
\text{Byte 0} &: \texttt{0xF0} \quad (\text{Exclusive Status}) \\
\text{Byte 1} &: \texttt{0x42} \quad (\text{Korg Manufacturer ID}) \\
\text{Byte 2} &: \texttt{0x4g} \quad (g = \text{Global MIDI Channel } 0..15) \\
\text{Byte 3} &: \texttt{0x00} \quad (\text{Software Project ID Byte 1}) \\
\text{Byte 4} &: \texttt{0x01} \quad (\text{Software Project ID Byte 2}) \\
\text{Byte 5} &: \texttt{0x04} \quad (\text{Software Project ID Byte 3 } [\text{nanoKONTROL } = \texttt{000104H}]) \\
\text{Byte 6} &: \texttt{0x00} \quad (\text{Device Sub ID}) \\
\text{Byte 7} &: \texttt{cd}   \quad (\text{Command Header: } 0, d, v, m, m, m, m, m) \\
\text{Byte 8..N} &: \text{Payload Data} \\
\text{Last Byte} &: \texttt{0xF7} \quad (\text{End of Exclusive})
\end{aligned}$$

Command Header Bitmask (`cd`):
- Bit 6 ($d$): Direction ($0 = \text{Host} \rightarrow \text{Controller}$, $1 = \text{Controller} \rightarrow \text{Host}$).
- Bit 5 ($v$): Format ($0 = 2\text{-Byte Format}$, $1 = \text{Variable Length}$).
- Bits 4..0 ($m$): Command Number.

### 4.2 Complete SysEx Command Reference

#### 1. Current Scene Data Dump Request (Host $\rightarrow$ Controller)
Requests the nanoKONTROL to transmit the entire parameter configuration of the currently active scene:
```text
F0 42 4g 00 01 04 00 1F 10 00 F7
```
- Response: nanoKONTROL transmits **Current Scene Data Dump** (`Func = 40H`) or NAK (`Func = 24H`).

#### 2. Current Scene Data Dump (Bidirectional)
Transmits or receives the complete $256\text{-byte}$ parameter block for the current scene (encoded into $293$ MIDI bytes):
```text
F0 42 4g 00 01 04 00 7F 7F 02 02 26 40 [293 Packed Data Bytes] F7
```
- When received by the nanoKONTROL, it updates its operational RAM for the active scene and transmits ACK (`Func = 23H`) or NAK (`Func = 24H`).

#### 3. Scene Write Request (Host $\rightarrow$ Controller)
Commits the current scene in RAM permanently into internal EEPROM Scene slot $0..3$:
```text
F0 42 4g 00 01 04 00 1F 11 0s F7
```
- `0s`: Destination Scene Number ($0 = \text{Scene 1}, 1 = \text{Scene 2}, 2 = \text{Scene 3}, 3 = \text{Scene 4}$).
- Response: nanoKONTROL transmits **Scene Change** (`Func = 4FH`) followed by **Write Completed** (`Func = 21H`) or **Write Error** (`Func = 22H`).

#### 4. Scene Change Request (Host $\rightarrow$ Controller)
Remotely switches the active scene on the nanoKONTROL hardware without touching the physical button:
```text
F0 42 4g 00 01 04 00 1F 14 0s F7
```
- `0s`: Target Scene Number ($0..3$).
- Response: nanoKONTROL switches its physical Scene LEDs, loads the scene into RAM, and transmits **Scene Change** (`Func = 4FH`) followed by **Data Load Completed** (`Func = 23H`).

#### 5. Handshake & Acknowledgment Messages (Controller $\rightarrow$ Host)
- **Data Load Completed (ACK)**: `F0 42 4g 00 01 04 00 5F 23 00 F7`
- **Data Load Error (NAK)**: `F0 42 4g 00 01 04 00 5F 24 00 F7`
- **Write Completed**: `F0 42 4g 00 01 04 00 5F 21 00 F7`
- **Write Error**: `F0 42 4g 00 01 04 00 5F 22 00 F7`
- **Scene Change Broadcast**: `F0 42 4g 00 01 04 00 5F 4F 0s F7` *(transmitted whenever the physical `[SCENE]` button is pressed!)*

---

## 5. The 7-Bit to 8-Bit SysEx Packing Algorithm

Because standard MIDI data bytes cannot have the most significant bit (MSB, Bit 7) set ($\le \texttt{0x7F}$), the nanoKONTROL compresses **$256$ unconstrained $8\text{-bit}$ raw bytes** into **$293$ safe $7\text{-bit}$ MIDI bytes** using standard Korg 7-to-8 bit shifting:

```
Raw Unpacked Data (7 Bytes x 8-bit):
Byte 0: [b7 b6 b5 b4 b3 b2 b1 b0]
Byte 1: [b7 b6 b5 b4 b3 b2 b1 b0]
Byte 2: [b7 b6 b5 b4 b3 b2 b1 b0]
Byte 3: [b7 b6 b5 b4 b3 b2 b1 b0]
Byte 4: [b7 b6 b5 b4 b3 b2 b1 b0]
Byte 5: [b7 b6 b5 b4 b3 b2 b1 b0]
Byte 6: [b7 b6 b5 b4 b3 b2 b1 b0]

Transmitted MIDI Data (8 Bytes x 7-bit):
MIDI 0: [ 0  B6.7 B5.7 B4.7 B3.7 B2.7 B1.7 B0.7 ]  <-- MSB Header Byte
MIDI 1: [ 0  B0.6 B0.5 B0.4 B0.3 B0.2 B0.1 B0.0 ]
MIDI 2: [ 0  B1.6 B1.5 B1.4 B1.3 B1.2 B1.1 B1.0 ]
MIDI 3: [ 0  B2.6 B2.5 B2.4 B2.3 B2.2 B2.1 B2.0 ]
MIDI 4: [ 0  B3.6 B3.5 B3.4 B3.3 B3.2 B3.1 B3.0 ]
MIDI 5: [ 0  B4.6 B4.5 B4.4 B4.3 B4.2 B4.1 B4.0 ]
MIDI 6: [ 0  B5.6 B5.5 B5.4 B5.3 B5.2 B5.1 B5.0 ]
MIDI 7: [ 0  B6.6 B6.5 B6.4 B6.3 B6.2 B6.1 B6.0 ]
```

### 5.1 Packing Mathematics
- Total raw bytes per scene: $256\text{ bytes}$.
- $256 \div 7 = 36$ full groups of 7 bytes ($36 \times 7 = 252\text{ bytes}$).
- $36\text{ groups} \times 8\text{ MIDI bytes} = 288\text{ MIDI bytes}$.
- Remaining bytes: $256 - 252 = 4\text{ raw bytes}$.
- The remaining 4 bytes require $1\text{ header byte} + 4\text{ data bytes} = 5\text{ MIDI bytes}$.
- Total transmitted payload: $288 + 5 = \mathbf{293\text{ bytes}}$.

### 5.2 Python Codec Implementation
The following Python functions can be embedded into custom tools to encode and decode nanoKONTROL scene memory blocks:

```python
from typing import List, Sequence

def unpack_nanokontrol_sysex(packed_data: Sequence[int]) -> List[int]:
    """Unpacks 293 7-bit MIDI bytes into 256 raw 8-bit parameter bytes."""
    unpacked = []
    src_idx = 0
    total_packed = len(packed_data)
    
    while src_idx < total_packed and len(unpacked) < 256:
        header = packed_data[src_idx]
        src_idx += 1
        
        chunk_len = min(7, 256 - len(unpacked))
        for bit in range(chunk_len):
            if src_idx >= total_packed:
                break
            byte_val = packed_data[src_idx]
            src_idx += 1
            msb = ((header >> bit) & 0x01) << 7
            unpacked.append(byte_val | msb)
            
    return unpacked

def pack_nanokontrol_sysex(raw_data: Sequence[int]) -> List[int]:
    """Packs 256 raw 8-bit parameter bytes into 293 7-bit MIDI bytes."""
    packed = []
    raw_len = len(raw_data)
    
    for i in range(0, raw_len, 7):
        chunk = raw_data[i:i + 7]
        header = 0
        for bit, byte_val in enumerate(chunk):
            if byte_val & 0x80:
                header |= (1 << bit)
        packed.append(header)
        for byte_val in chunk:
            packed.append(byte_val & 0x7F)
            
    return packed
```

---

## 6. Complete 256-Byte Scene Parameter Memory Map

Every scene in the nanoKONTROL is represented internally by a fixed-size $256\text{-byte}$ memory structure.

### 6.1 Common Parameters (Offsets 0 to 15)

| Byte Offset | Parameter Name | Valid Range | Description |
|---|---|---|---|
| **`0..11`** | **Scene Name** | ASCII ($32..126$) | 12-character ASCII text (padded with spaces, no null terminator) |
| **`12`** | **Scene MIDI Channel** | `0..15` | Default MIDI Channel for this scene ($0 = \text{Ch 1}, 15 = \text{Ch 16}$) |
| **`13..15`** | **Reserved / Dummy** | `0` | Reserved for internal alignment (must be set to `0`) |

---

### 6.2 MIDI Control Group Parameters (Blocks 1 to 9)
Each of the 9 vertical strips occupies exactly **23 bytes**:
$$\text{Block Offset}(k) = 16 + (k - 1) \times 23 \quad \text{for } k \in [1..9]$$

| Block | Relative Offset | Absolute Range | Parameter Function |
|---|---|---|---|
| **Block 1** | $+0 \dots +22$ | `16 .. 38` | Strip 1 (Fader 1, Knob 1, Button A1, Button B1) |
| **Block 2** | $+0 \dots +22$ | `39 .. 61` | Strip 2 (Fader 2, Knob 2, Button A2, Button B2) |
| **Block 3** | $+0 \dots +22$ | `62 .. 84` | Strip 3 (Fader 3, Knob 3, Button A3, Button B3) |
| **Block 4** | $+0 \dots +22$ | `85 .. 107`| Strip 4 (Fader 4, Knob 4, Button A4, Button B4) |
| **Block 5** | $+0 \dots +22$ | `108 .. 130`| Strip 5 (Fader 5, Knob 5, Button A5, Button B5) |
| **Block 6** | $+0 \dots +22$ | `131 .. 153`| Strip 6 (Fader 6, Knob 6, Button A6, Button B6) |
| **Block 7** | $+0 \dots +22$ | `154 .. 176`| Strip 7 (Fader 7, Knob 7, Button A7, Button B7) |
| **Block 8** | $+0 \dots +22$ | `177 .. 199`| Strip 8 (Fader 8, Knob 8, Button A8, Button B8) |
| **Block 9** | $+0 \dots +22$ | `200 .. 222`| Strip 9 (Fader 9, Knob 9, Button A9, Button B9) |
| **Padding**| — | `223` | Dummy padding byte (must be `0`) |

#### Internal Parameter Breakdown within Each 23-Byte Block

| Relative Offset | Parameter | Value Range | Functional Meaning |
|---|---|---|---|
| **`+0`** | **Block MIDI Channel** | `0..15` / `16` | `0..15`: Discrete Ch 1..16; `16`: Follow Scene MIDI Channel |
| **`+1`** | **Slider Assign Type** | `0..1` | `0`: Disabled (`No Assign`); `1`: `Control Change` |
| **`+2`** | **Slider CC#** | `0..127` | MIDI CC transmitted by the slider |
| **`+3`** | **Slider Min Value** | `0..127` | Value at bottom of slider travel (default $0$) |
| **`+4`** | **Slider Max Value** | `0..127` | Value at top of slider travel (default $127$) |
| **`+5`** | **Knob Assign Type** | `0..1` | `0`: Disabled (`No Assign`); `1`: `Control Change` |
| **`+6`** | **Knob CC#** | `0..127` | MIDI CC transmitted by the knob |
| **`+7`** | **Knob Min Value** | `0..127` | Value at full CCW position (default $0$) |
| **`+8`** | **Knob Max Value** | `0..127` | Value at full CW position (default $127$) |
| **`+9`** | **Button A Assign Type** | `0..2` | `0`: Disabled; `1`: `Control Change`; `2`: `MIDI Note` |
| **`+10`**| **Button A CC# / Note#** | `0..127` | CC number or MIDI Note number ($0..127 = \text{C-1 to G9}$) |
| **`+11`**| **Button A Off Value** | `0..127` | CC value sent on release (only when Assign Type = CC) |
| **`+12`**| **Button A On Value** | `0..127` | CC value on press, or Note-On Velocity ($1..127$) |
| **`+13`**| **Button A Attack Time**| `0..127` | CC ramp-up time ($0 = \text{instant}, 127 = \text{maximum slew}$) |
| **`+14`**| **Button A Release Time**| `0..127`| CC decay time ($0 = \text{instant}, 127 = \text{maximum slew}$) |
| **`+15`**| **Button A Switch Type**| `0..1` | `0`: `Momentary`; `1`: `Toggle` |
| **`+16`**| **Button B Assign Type** | `0..2` | `0`: Disabled; `1`: `Control Change`; `2`: `MIDI Note` |
| **`+17`**| **Button B CC# / Note#** | `0..127` | CC number or MIDI Note number |
| **`+18`**| **Button B Off Value** | `0..127` | CC value sent on release |
| **`+19`**| **Button B On Value** | `0..127` | CC value on press, or Note-On Velocity |
| **`+20`**| **Button B Attack Time**| `0..127` | CC ramp-up time |
| **`+21`**| **Button B Release Time**| `0..127`| CC decay time |
| **`+22`**| **Button B Switch Type**| `0..1` | `0`: `Momentary`; `1`: `Toggle` |

---

### 6.3 Transport Switch Parameters (Offsets 224 to 255)
The 6 transport buttons occupy offsets `224` through `254`:

| Offset | Parameter | Value Range | Functional Meaning |
|---|---|---|---|
| **`224`** | **Transport MIDI Channel** | `0..15` / `16` | `0..15`: Discrete Ch 1..16; `16`: Follow Scene MIDI Channel |
| **`225`** | **SW 1 (`REW`) Assign Type** | `0..2` | `0`: No Assign; `1`: `Control Change`; `2`: `MMC` |
| **`226`** | **SW 1 (`REW`) CC#** | `0..127` | CC number (valid if Assign Type = CC) |
| **`227`** | **SW 1 (`REW`) MMC Command** | `0..12` | MMC command ($4 = \text{Rewind}$, see Table below) |
| **`228`** | **SW 1 (`REW`) MMC Device ID**| `0..127` | Target MMC ID ($127 = \text{All-Call}$) |
| **`229`** | **SW 1 (`REW`) Switch Type** | `0..1` | `0`: Momentary; `1`: Toggle (forced Momentary if MMC) |
| **`230..234`** | **SW 2 (`PLAY`) Parameters** | — | Same 5-byte format as SW 1 (Default MMC = `1` / Play) |
| **`235..239`** | **SW 3 (`FF`) Parameters** | — | Same 5-byte format as SW 1 (Default MMC = `3` / Fast Fwd) |
| **`240..244`** | **SW 4 (`LOOP`) Parameters** | — | Same 5-byte format as SW 1 (Default Assign = CC) |
| **`245..249`** | **SW 5 (`STOP`) Parameters** | — | Same 5-byte format as SW 1 (Default MMC = `0` / Stop) |
| **`250..254`** | **SW 6 (`REC`) Parameters** | — | Same 5-byte format as SW 1 (Default MMC = `5` / Rec Strobe) |
| **`255`** | **Padding / Dummy** | `0` | Reserved byte (must be `0`) |

*Total Size: Exactly $256\text{ bytes}$.*

---

## 7. Configuration & File Management

### 7.1 Korg Kontrol Editor File Formats
When saving configurations using the official Korg Kontrol Editor, files are saved with two specific extensions:
1. **`.nktrl_data` (Single Scene File)**:
   - Contains parameter data for **one individual scene** ($256$ uncompressed parameter bytes).
2. **`.nktrl_set` (Full Scene Set File)**:
   - Contains parameter data for **all 4 scenes** ($4 \times 256 = 1024$ uncompressed parameter bytes).

### 7.2 Headless Linux & Python Tooling (Bypassing Official Editor)
Because nanoKONTROL uses class-compliant MIDI SysEx, you can backup, inspect, and reprogram scenes on Linux or Zynthian without needing Windows/Mac software:

#### Backing up Current Scene to a SysEx File via `amidi`
```bash
# 1. Identify nanoKONTROL rawmidi port
amidi -l

# 2. Request and record Current Scene Data Dump
amidi -p hw:1,0 -S "F0 42 40 00 01 04 00 1F 10 00 F7" -r nanokontrol_scene1_dump.syx -t 2
```

#### Uploading a SysEx File into nanoKONTROL RAM
```bash
amidi -p hw:1,0 -s nanokontrol_custom_scene.syx
```

#### Committing RAM to Hardware Scene 1 EEPROM
```bash
# Writes current RAM to Scene 0 (Scene 1 on faceplate)
amidi -p hw:1,0 -S "F0 42 40 00 01 04 00 1F 11 00 F7"
```

---

## 8. Zynthian Integration Blueprint (Stage 2 Architecture)

In the [`mc-zynthian`](../README.md) architecture, the nanoKONTROL v1 is deployed to provide immediate tactile mixing and transport control, liberating the touchscreen and macro keyboard for deep system views.

```
Scene 1: Master DAW & 8-Track Mixer Strip
Scene 2: Active Synth Voice Deep Parameter Editing
Scene 3: Step Sequencer, Zynpad & Pattern Triggering
Scene 4: Roland MC-101 Dedicated External Hardware Companion
```

### 8.1 Scene 1: Master DAW & 8-Track Mixer Strip
- **Faders 1–8**: Volume faders for Zynthian Chains $1$ through $8$ (`zynmixer` volume).
- **Fader 9**: Master Output Volume (`zynmixer` main level).
- **Knobs 1–8**: Stereo Panning for Chains $1$ through $8$.
- **Knob 9**: Global Reverb / Master FX Send level.
- **Buttons A1–A8 (Upper)**: Track Mute toggles for Chains $1$ through $8$.
- **Buttons B1–B8 (Lower)**: Track Solo toggles for Chains $1$ through $8$.
- **Buttons A9 / B9**: All Notes Off (Panic) / Master Mute.
- **Transport Buttons**:
  - `[PLAY]`: Start Sequencer (`/cuia/toggle_play`).
  - `[STOP]`: Stop Sequencer & Audio.
  - `[REC]`: Toggle Step/Live MIDI Recording (`/cuia/toggle_midi_record`).
  - `[REW]`: Jump to Measure 1 (`/cuia/seq_first`).
  - `[FF]`: Jump to Next Pattern.
  - `[LOOP]`: Toggle Loop playback.

### 8.2 Scene 2: Active Synth Voice Deep Parameter Editing
When tweaking synth engines (e.g., Dexed, OB-Xd, Surge, or Roland Zen-Core):
- **Sliders 1–4**: Amplifier Envelope (Attack, Decay, Sustain, Release).
- **Sliders 5–8**: Filter Envelope (Attack, Decay, Sustain, Release).
- **Slider 9**: Envelope to Filter Modulation Depth.
- **Knobs 1–4**: Filter Cutoff, Resonance, Filter Drive, Key Tracking.
- **Knobs 5–8**: LFO 1 Rate, LFO 1 Depth, LFO 2 Rate, LFO 2 Depth.
- **Knob 9**: Master Tuning / Chorus Mix.
- **Buttons A1–A9 / B1–B9**: Waveform toggles, Filter Slope ($12\text{ dB} / 24\text{ dB}$), and Arpeggiator on/off.

### 8.3 Scene 4: Roland MC-101 Live Companion Hub
When performing alongside the Roland MC-101 (leveraging [`docs/mc101-guide.md`](mc101-guide.md)):
- **Faders 1–4**: Roland MC-101 Track Volumes (Ch 1–4 `CC 7`).
- **Faders 5–8**: Zynthian Sub-Mix Tracks.
- **Knobs 1–4**: MC-101 Sound / Cutoff Controls (Ch 1–4 `CC 74`).
- **Buttons A1–A4**: MC-101 Clip Launchers / Track Mutes.
- **Buttons B1–B4**: MC-101 Scatter Pad triggers (Ch 13 Note triggers).

---

## 9. Comprehensive Troubleshooting & Hardware Diagnostics

### 9.1 Diagnostic Checklist

| Diagnostic Task | Terminal Command | Expected Output |
|---|---|---|
| Verify USB Hardware Enumeration | `lsusb -d 0944:0104` | `Bus 001 Device 004: ID 0944:0104 KORG, Inc. nanoKONTROL` |
| Verify ALSA RawMIDI Client | `amidi -l` | `IO  hw:1,0,0  nanoKONTROL MIDI 1` |
| Monitor Incoming MIDI Messages | `aseqdump -p "nanoKONTROL"` | Real-time stream of `Control change` and `Note on/off` |
| Test Device Inquiry Handshake | `amidi -p hw:1,0 -S "F0 7E 7F 06 01 F7" -t 1` | Returns `F0 7E 00 06 02 42 04 01 00 00 ... F7` |

### 9.2 Common Issues & Resolutions

#### 1. Hardware Fails to Power On
- **Symptom**: No Scene LEDs illuminate when plugging in the USB cable.
- **Cause**: Inadequate power from an unpowered USB hub or degraded USB Mini-B cable.
- **Solution**: Connect directly to one of the Raspberry Pi 4's blue USB 3.0 ports, or use a powered USB hub. Verify the USB cable by testing continuity.

#### 2. Buttons "Stuck" On or Behaving Errantly
- **Symptom**: Pressing a button leaves its parameter on, requiring a second press to release.
- **Cause**: Button is set to `Toggle` mode instead of `Momentary` mode in the active scene configuration.
- **Solution**: Reload a momentary template or perform a Factory Reset (`[REC] + [STOP] + [SCENE]` during power-up).

#### 3. Sliders or Knobs Ramping Unintentionally
- **Symptom**: Moving a fader causes values to lag or creep slowly to their target.
- **Cause**: An inadvertent Attack/Release time was assigned to the control group in the scene memory map.
- **Solution**: Open the scene in Korg Kontrol Editor (or flash a clean dump) and verify that Attack Time and Release Time are set to `0`.

---

## 10. Technical Authority & Reference Links

1. **Korg Official Documentation**:
   - [Korg nanoKONTROL Owner's Manual (PDF)](https://www.korg.com/)
   - [Korg nanoKONTROL MIDI Implementation Chart (2009.10.06)](https://www.korg.com/)
   - [Korg nanoKONTROL MIDI Implementation (Revision 1.00, 2008.12.04)](https://www.korg.com/)
   - [KORG KONTROL Editor Owner's Manual](https://www.korg.com/)
2. **mc-zynthian Project Documentation & Ecosystem**:
   - Master Roadmap & Architecture: [`README.md`](../README.md)
   - Pisound Guide: [`docs/pisound-guide.md`](pisound-guide.md)
   - Ableton Push 1 Hardware Guide: [`docs/push-guide.md`](push-guide.md)
   - Ableton Push 1 Technical Protocols: [`docs/push-protocols.md`](push-protocols.md)
   - Roland MC-101 Operational Reference: [`docs/mc101-guide.md`](mc101-guide.md)
   - Roland MC-101 SysEx & Memory Architecture: [`docs/mc101-sysex.md`](mc101-sysex.md)
   - Macro Keyboard Guide: [`docs/macrokeyboard-guide.md`](macrokeyboard-guide.md)

