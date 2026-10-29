# Roland MC-101 System Exclusive (SysEx) Reference & Rosetta Stone

## Sources of Information

This document consolidates and cross-verifies all known System Exclusive (SysEx) research for the Roland MC-101 / MC-707 / ZEN-Core platform from the following primary authorities:

1. **MC-707 Toolbox (`zencore_mc707toolbox.md` & `param-docs.mjs`)**: Parameter database derived from Roland ZEN-Core data models, decoded via [Roland-Zen-Decode-XML](https://github.com/DrKnackeratorStrikesAgain/Roland-Zen-Decode-XML) by DrKnackerator, cross-referenced with `mc-programmer` and `mctools_basic`, and tested on Roland hardware. Primary authority for block layouts, offsets, data encodings, value ranges, and MFX definitions.
2. **`nanonontroller.py` Live Research (RowdyVoyeur)**: Reverse engineering, address sweeping (98,512 responding blocks mapped), 4-pass differential verification on live MC-101 hardware, pad-to-MIDI note tables, and real-world latency/timeout measurements.
3. **`MC-101 Editor` (Benedetto Schiavone / "benis67")**: Analysis of SysEx formulas, defining dynamic base calculation, analog-model parameters, and mixer offset families.
4. **Olivier Smet's MC-101 Address Sweep**: Address map exploration and full RQ1 sweep documenting block limits and responding regions.
5. **Roland Fantom-06/07/08 MIDI Implementation**: Structural reference for standard ZEN-Core PCM/VA/LFO parameter layout and nibble packing rules.
6. **Splunge ZenInspector & Project File Structure**: Analysis of Roland `.mpj` / SVZ structure confirming the offline-only nature of the Drum Inst record layer.

---

## 1. Executive Summary & Architecture

The Roland MC-101 implements a full 4-partial ZEN-Core synthesizer engine, 4 tracks (each assignable to Tone, Drum Kit, or Looper), and a multi-effects (MFX) processor per track. Although Roland has never published an official MIDI Implementation Chart or SysEx manual for the MC-101, the internal firmware shares the address architecture with the Roland MC-707, Verselab MV-1, and Fantom.

### Core Principles
- **Addressing Formula**: Every SysEx message targets a memory address calculated as:
  $$\text{Target Address} = \text{Object Base} + \text{Block Offset} + \text{Parameter Offset}$$
- **Model IDs**: The MC-101 responds to Model ID `00 00 00 5E` (MC-101 specific) as well as `00 00 00 5B` (standard ZEN-Core family / Fantom / MC-707). Both are valid DT1/RQ1 model headers.
- **Device ID**: Default is `10` hex (`16` 0-indexed, `17` 1-indexed).
- **Working Buffers vs Storage**: Parameter edits made to a clip's active sound operate directly on the track's live temporary object buffer (Slot 17 / index 16 of each track).
- **SysEx vs Performance MIDI**: Performance gestures (Scatter pads, transport, standard CC controls) use standard MIDI channel messages, not SysEx:
  - **Scatter**: MIDI Note On/Off notes `60`..`75` on MIDI Channel 13.
  - **Transport**: Standard MIDI Realtime commands (`0xFA` Start, `0xFC` Stop).
  - **Performance Knobs / Macros**: Standard MIDI CCs on Channels 1..4.

---

## 2. SysEx Message Framing & Protocols

### 2.1 DT1 Data Set 1 (Write)
Used to write one or more parameters to the MC-101.

```
F0 41 [dev] 00 00 00 [model] 12 aa bb cc dd [data...] [checksum] F7
```

| Byte | Field | Value / Description |
|---|---|---|
| 0 | Start | `F0` (SysEx Begin) |
| 1 | Manufacturer | `41` (Roland Corporation) |
| 2 | Device ID | `10` (Default device ID; 0x10) |
| 3-6 | Model ID | `00 00 00 5E` (MC-101) or `00 00 00 5B` (ZEN-Core family) |
| 7 | Command | `12` (DT1: Data Set 1) |
| 8-11 | Address | `aa bb cc dd` (4 bytes, 7-bit each: 0x00..0x7F) |
| 12..n | Data | One or more 7-bit data bytes |
| n+1 | Checksum | Roland checksum over address bytes + data bytes |
| n+2 | End | `F7` (SysEx End) |

### 2.2 RQ1 Data Request 1 (Read)
Used to request data from the MC-101. Non-destructive; safe for probing or syncing state.

```
F0 41 [dev] 00 00 00 [model] 11 aa bb cc dd ss tt uu vv [checksum] F7
```

| Byte | Field | Value / Description |
|---|---|---|
| 0-6 | Header | `F0 41 10 00 00 00 5E` (or `5B`) |
| 7 | Command | `11` (RQ1: Data Request 1) |
| 8-11 | Address | `aa bb cc dd` (Target starting address) |
| 12-15 | Size | `ss tt uu vv` (Requested size, 4 bytes, 7-bit packed) |
| 16 | Checksum | Roland checksum over address bytes + size bytes |
| 17 | End | `F7` |

#### Hardware Read Behaviors
1. **Truncation to Real Block Size**: If you request more bytes than a block contains (e.g. requesting 128 bytes `00 00 01 00` on a 27-byte drum partial), the MC-101 truncates the DT1 reply to the exact block length.
2. **Silence on Invalid Address**: If an address is unmapped, the MC-101 sends **no reply** (no NACK or error frame). Silence signifies an invalid or unmapped address.
3. **Latency**: Measured reply latency: 58 ms min, 59 ms median, 508 ms outlier. Safe timeout is 200 ms for bulk polling, 600 ms absolute.

### 2.3 Roland Checksum Calculation
The checksum covers the 4 address bytes plus all data (or size) bytes.

$$\text{sum} = \left(\sum \text{address\_bytes} + \sum \text{data\_or\_size\_bytes}\right) \pmod{128}$$
$$\text{checksum} = (128 - \text{sum}) \pmod{128}$$

#### Python Reference Implementation
```python
def roland_checksum(payload: list[int]) -> int:
    """Calculates Roland 7-bit checksum over address + data/size bytes."""
    return (128 - (sum(payload) % 128)) % 128

def build_dt1(address: list[int], data: list[int], model_id: int = 0x5E) -> bytes:
    payload = address + data
    chk = roland_checksum(payload)
    return bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, model_id, 0x12] + payload + [chk, 0xF7])

def build_rq1(address: list[int], size: list[int], model_id: int = 0x5E) -> bytes:
    payload = address + size
    chk = roland_checksum(payload)
    return bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, model_id, 0x11] + payload + [chk, 0xF7])
```

---

## 3. Data Encodings & Wire Formats

Roland SysEx values must conform to MIDI 7-bit bytes (`0x00`..`0x7F`). Multi-byte values and negative ranges are packed using specific rules:

| Encoding Type | Wire Size | Description & Conversion |
|---|---|---|
| `7-bit` | 1 byte | Direct unsigned integer `0`..`127`. |
| `7-bit, +64` | 1 byte | Centred / signed value. Add `64` before transmission. Display $-64 \dots +63 \rightarrow$ Wire $0 \dots 127$. |
| `2 nibbles` | 2 bytes | Value split into two 4-bit nibbles (Big-Endian): `[(V >> 4) & 0x0F, V & 0x0F]`. |
| `2 nibbles, +128` | 2 bytes | Value offset by $+128$, then split into 2 nibbles. (e.g. range $-100 \dots +100 \rightarrow 28 \dots 228$). |
| `4 nibbles` | 4 bytes | 16-bit integer split into four 4-bit nibbles (Big-Endian): `[(V >> 12) & 0xF, (V >> 8) & 0xF, (V >> 4) & 0xF, V & 0xF]`. |
| `4 nibbles, +k` | 4 bytes | Add offset $k$ first, then 4 nibbles: <br>• **MFX Parameters**: $k = +32768$ (stored $-20000 \dots +20000$)<br>• **Pitch/Filter Env Levels**: $k = +1024$<br>• **EQ Gains**: $k = +1024$ (range $-240 \dots +240$) |
| `text` | 16 bytes | 16 ASCII characters, one 7-bit byte per character. |

---

## 4. Complete Address Model & Memory Map

A full hardware sweep (`00 00 00 00` to `7F 7F 7F 7F`) confirms that only the following high-level regions respond on the MC-101:

| First Byte (`b1`) | Subsystem | Description & Capacity |
|---|---|---|
| `00` | System | Device system configuration (1 block) |
| `10` | Project | Project parameters (tempo, master sync, global settings) |
| `20` - `28` | Clips | 136 clips (8 tracks $\times$ 17 clip slots), stride `00 08 00 00` |
| `29` | Clip Tail | Tail of the clip memory pool |
| `30` - `32` | Clip Tone | 136 Tone sound structures (PCM/VA), stride `00 02 00 00` |
| `32` - `35` | Clip Rhythm | 136 Drum Kit structures, stride `00 03 00 00` |
| `40` - `41` | SN-Style Tone | SuperNATURAL style tone model |
| `50` | Storage: Tones | 64 User Tone memory slots |
| `52` - `53` | Storage: Drum Kits | 64 User Drum Kit memory slots |

*Note*: Address spaces `36`-`39`, `42`-`4F`, `54`-`7F`, `70` (Project2), and `7A` (ZBCtrl) are inactive/silent on MC-101.

### 4.1 Track Working Buffers (Slot 17 Architecture)
Each track region is partitioned for 8 tracks $\times$ 17 clip slots (inherited from the MC-707 descriptor table). **Slot 17 (index 16, 0-based) is the active temporary object buffer loaded in RAM for live playback and editing.**

| Track Number | Slot Index | Active Tone Base Address | Active Drum Kit Base Address |
|---|---|---|---|
| **Track 1** | 16 | `30 20 00 00` | `32 40 00 00` |
| **Track 2** | 33 | `30 42 00 00` | `32 73 00 00` |
| **Track 3** | 50 | `30 64 00 00` | `33 26 00 00` |
| **Track 4** | 67 | `31 06 00 00` | `33 59 00 00` |

*(Tracks 5–8 exist in the internal descriptor map but are unassigned on the 4-track MC-101).*

---

### 4.2 Tone Slot Layout (All Blocks)

Within any active Tone base address, individual parameter blocks are located at the following offsets:

| Block | Description | Offset from Tone Base | Count | Step Between Copies | Total Block Length |
|---|---|---|---|---|---|
| **CMN** | Tone Common | `00 00 00 00` | 1 | — | 54 bytes |
| **MFX** | Multi-Effects | `00 00 01 00` | 1 | — | 144 bytes |
| **PMT** | Partial Mute / Velocity / Range | `00 00 10 00` | 1 | — | 38 bytes |
| **PTL** | Partial Parameters (P1..P4) | `00 00 20 00` | 4 | `00 00 01 00` | 128 bytes |
| **PENV** | Pitch Envelope (P1..P4) | `00 00 24 00` | 4 | `00 00 01 00` | 45 bytes |
| **FENV** | Filter Envelope (P1..P4) | `00 00 28 00` | 4 | `00 00 01 00` | 44 bytes |
| **AENV** | Amp Envelope (P1..P4) | `00 00 2C 00` | 4 | `00 00 01 00` | 32 bytes |
| **LFO** | LFO 1 & 2 (P1..P4) | `00 00 30 00` | 4 | `00 00 02 00` | 158 bytes |
| **EQ** | 3-Band Parametric EQ (P1..P4) | `00 00 38 00` | 4 | `00 00 01 00` | 27 bytes |
| **SCMN** | Synth Common (Unison, Drift) | `00 00 3C 00` | 1 | — | 9 bytes |
| **SPMT** | Synth Structure / CrossMod / Ring | `00 00 3D 00` | 1 | — | 23 bytes |
| **SPTL** | Synth Partial (OSC, VA, VCF) (P1..P4) | `00 00 3E 00` | 4 | `00 00 01 00` | 29 bytes |

#### Tone Partial Address Calculation
For Partial $P \in \{1, 2, 3, 4\}$:
$$\text{PTL Address} = \text{Tone Base} + \text{PTL Offset} + ((P - 1) \times \text{0x0100}) + \text{Param Offset}$$
$$\text{LFO Address} = \text{Tone Base} + \text{LFO Offset} + ((P - 1) \times \text{0x0200}) + \text{Param Offset}$$

---

### 4.3 Drum Kit Slot Layout (All Blocks)

Within any active Drum Kit base address:

| Block | Description | Offset from Drum Base | Count | Step Between Copies | Total Block Length |
|---|---|---|---|---|---|
| **KCMN** | Drum Kit Common | `00 00 00 00` | 1 | — | 25 bytes |
| **MFX** | Drum Kit Multi-Effects | `00 00 01 00` | 1 | — | 144 bytes |
| **KCMP** | Drum Compressors (Comp 1..6) | `00 00 10 00` | 6 | `00 00 01 00` | 8 bytes |
| **KPTL** | Drum Partial (Keys 21..108) | `00 00 16 00` | 88 | `00 00 01 00` | 27 bytes |
| **KEQ** | Drum Partial EQ (Keys 21..108) | `00 00 6E 00` | 88 | `00 00 01 00` | 27 bytes |

#### Drum Key / Pad Base Calculation
Drum partials correspond to MIDI notes $21 \dots 108$ (A0 to C8). Partials are indexed by MIDI pitch:
$$\text{drum\_key\_base} = \text{drum\_track\_base} + \left(00.00.(0\text{x}16 + \text{key} - 21).00\right)$$
$$\text{drum\_eq\_base} = \text{drum\_track\_base} + \left(00.00.(0\text{x}6E + \text{key} - 21).00\right)$$

#### Physical Pad to MIDI Pitch & SysEx Address Map (Track 1 Example)
The 16 physical pads on the MC-101 send standard note numbers that map to specific drum key offsets:

| Pad # | MIDI Note | Note Name | Track 1 Drum Key Partial Base (`KPTL`) | Track 1 Drum EQ Base (`KEQ`) |
|---|---|---|---|---|
| **Pad 1** | 37 | C#2 | `32 40 26 00` | `32 40 7E 00` |
| **Pad 2** | 39 | D#2 | `32 40 28 00` | `32 40 80 00` $\rightarrow$ `32 41 00 00` |
| **Pad 3** | 42 | F#2 | `32 40 2B 00` | `32 41 03 00` |
| **Pad 4** | 46 | A#2 | `32 40 2F 00` | `32 41 07 00` |
| **Pad 5** | 49 | C#3 | `32 40 32 00` | `32 41 0A 00` |
| **Pad 6** | 51 | D#3 | `32 40 34 00` | `32 41 0C 00` |
| **Pad 7** | 54 | F#3 | `32 40 37 00` | `32 41 0F 00` |
| **Pad 8** | 56 | G#3 | `32 40 39 00` | `32 41 11 00` |
| **Pad 9** | 36 | C2 | `32 40 25 00` | `32 40 7D 00` |
| **Pad 10** | 38 | D2 | `32 40 27 00` | `32 40 7F 00` |
| **Pad 11** | 41 | F2 | `32 40 2A 00` | `32 41 02 00` |
| **Pad 12** | 45 | A2 | `32 40 2E 00` | `32 41 06 00` |
| **Pad 13** | 48 | C3 | `32 40 31 00` | `32 41 09 00` |
| **Pad 14** | 62 | D4 | `32 40 3F 00` | `32 41 17 00` |
| **Pad 15** | 63 | D#4 | `32 40 40 00` | `32 41 18 00` |
| **Pad 16** | 64 | E4 | `32 40 41 00` | `32 41 19 00` |

---

## 5. Tone ZEN-Core Parameter Specifications

### 5.1 CMN: Tone Common Block (`offset 00 00 00 00`, len 54)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 16 | — | — | text | `NAME` | Tone Name | 16 ASCII characters |
| `00 00 00 10` | 1 | 0..49 | 0 | 7-bit | `CATEGORY` | Category | Category ID |
| `00 00 00 15` | 1 | 0..127 | 127 | 7-bit | `LEVEL` | Tone Level | 0..127 |
| `00 00 00 16` | 1 | -64..63 | 0 | 7-bit, +64 | `PAN` | Tone Pan | L64..C..R63 |
| `00 00 00 17` | 1 | 0..1 | 0 | 7-bit | `PRIORITY` | Voice Priority | 0: LAST, 1: LOUDEST |
| `00 00 00 18` | 1 | -48..48 | 0 | 7-bit, +64 | `PIT_CRS` | Tone Coarse Tune | Semitones (-48..+48) |
| `00 00 00 19` | 1 | -50..50 | 0 | 7-bit, +64 | `PIT_FINE` | Tone Fine Tune | Cents (-50..+50) |
| `00 00 00 1A` | 1 | -3..3 | 0 | 7-bit, +64 | `OCTAVE` | Octave Shift | -3..+3 Octaves |
| `00 00 00 1B` | 1 | 0..3 | 0 | 7-bit | `STRETCH` | Stretch Tune Depth | 0: OFF, 1, 2, 3 |
| `00 00 00 1C` | 1 | 0..127 | 0 | 7-bit | `ANALOG_FEEL` | Analog Feel | 0..127 |
| `00 00 00 1D` | 1 | 0..1 | 1 | 7-bit | `MONO_POLY` | Mono / Poly Mode | 0: MONO, 1: POLY |
| `00 00 00 1E` | 1 | 0..1 | 0 | 7-bit | `LEGATO_SW` | Legato Switch | 0: OFF, 1: ON |
| `00 00 00 1F` | 1 | 0..13 | 12 | 7-bit | `RETRIG_INTVL` | Legato Retrig Intvl | 0..12, 13: OFF |
| `00 00 00 20` | 1 | 0..1 | 0 | 7-bit | `PORTA_SW` | Portamento Switch | 0: OFF, 1: ON |
| `00 00 00 21` | 1 | 0..1 | 0 | 7-bit | `PORTA_MODE` | Portamento Mode | 0: NORMAL, 1: LEGATO |
| `00 00 00 22` | 1 | 0..1 | 0 | 7-bit | `PORTA_TYPE` | Portamento Type | 0: RATE, 1: TIME |
| `00 00 00 23` | 1 | 0..1 | 0 | 7-bit | `PORTA_START` | Portamento Start | 0: PITCH, 1: NOTE |
| `00 00 00 24` | 4 | 0..1023 | 73 | 4 nibbles | `PORTA_TIME` | Portamento Time | 0..1023 |
| `00 00 00 28` | 1 | 0..48 | 2 | 7-bit | `BEND_RANGE_UP`| Bend Range Up | 0..48 semitones |
| `00 00 00 29` | 1 | 0..48 | 2 | 7-bit | `BEND_RANGE_DW`| Bend Range Down | 0..48 semitones |
| `00 00 00 2A` | 1 | 0..1 | 0 | 7-bit | `BEND_MODE` | Bend Mode | 0: NORMAL, 1: CATCH+LAST |
| `00 00 00 2B` | 1 | 0..100 | 0 | 7-bit | `SOFT_LEVEL_SENS`| Soft Level Sens | 0..100 |
| `00 00 00 34` | 1 | 0..2 | 0 | 7-bit | `PORTA_CRV` | Portamento Curve | 0..2 |
| `00 00 00 35` | 1 | 0..1 | 0 | 7-bit | `PTL_LFO_LOCK` | Partial LFO Phase Lock | 0: OFF, 1: ON |

---

### 5.2 PMT: Partial Mute / Key & Velocity Range (`offset 00 00 10 00`, len 38)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..3 | 1 | 7-bit | `VEL_CTRL` | Velocity Control Mode | 0: OFF, 1: ON, 2: RANDOM, 3: CYCLE |
| `00 00 00 01` | 1 | 0..1 | 0 | 7-bit | `PMT_LEVEL_CRV` | PMT Level Curve | 0: EXP, 1: LINEAR |
| `00 00 00 02` | 1 | 0..1 | 1 | 7-bit | `PMT1_PTL_SW` | Partial 1 Switch | 0: OFF, 1: ON |
| `00 00 00 03` | 1 | 0..127 | 0 | 7-bit | `PMT1_KRANGE_LO`| Partial 1 KeyRange Low | Note C-1..G9 |
| `00 00 00 04` | 1 | 0..127 | 127 | 7-bit | `PMT1_KRANGE_UP`| Partial 1 KeyRange Up | Note C-1..G9 |
| `00 00 00 05` | 1 | 0..127 | 0 | 7-bit | `PMT1_KFADE_LO` | Partial 1 KeyFade Low | 0..127 |
| `00 00 00 06` | 1 | 0..127 | 0 | 7-bit | `PMT1_KFADE_UP` | Partial 1 KeyFade Up | 0..127 |
| `00 00 00 07` | 1 | 1..127 | 1 | 7-bit | `PMT1_VRANGE_LO`| Partial 1 VeloRange Low| 1..127 |
| `00 00 00 08` | 1 | 1..127 | 127 | 7-bit | `PMT1_VRANGE_UP`| Partial 1 VeloRange Up | 1..127 |
| `00 00 00 09` | 1 | 0..127 | 0 | 7-bit | `PMT1_VFADE_LO` | Partial 1 VeloFade Low | 0..127 |
| `00 00 00 0A` | 1 | 0..127 | 0 | 7-bit | `PMT1_VFADE_UP` | Partial 1 VeloFade Up | 0..127 |
| *(Offsets repeat for Partials 2, 3, and 4 in steps of 9 bytes: P2 switch at `00 00 00 0B`, P3 switch at `00 00 00 14`, P4 switch at `00 00 00 1D`)* |

---

### 5.3 PTL: Tone Partial Block (`offset 00 00 20 00`, step `01 00`, len 128)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..127 | 127 | 7-bit | `LEVEL` | Partial Level | 0..127 |
| `00 00 00 01` | 1 | -48..48 | 0 | 7-bit, +64 | `PIT_CRS` | Coarse Tune | Semitones (-48..+48) |
| `00 00 00 02` | 1 | -50..50 | 0 | 7-bit, +64 | `PIT_FINE` | Fine Tune | Cents (-50..+50) |
| `00 00 00 03` | 4 | 0..1200 | 0 | 4 nibbles | `PIT_RND` | Random Pitch Depth | 0..1200 cents |
| `00 00 00 07` | 1 | -64..63 | 0 | 7-bit, +64 | `PAN` | Partial Pan | L64..C..R63 |
| `00 00 00 08` | 2 | -100..100 | 0 | 2 nibbles, +128| `PAN_KF` | Pan Keyfollow | -100..+100 |
| `00 00 00 0A` | 1 | 0..63 | 0 | 7-bit | `PAN_RND` | Random Pan Depth | 0..63 |
| `00 00 00 0B` | 1 | -64..63 | 0 | 7-bit, +64 | `PAN_ALT` | Alternate Pan Depth | -64..+63 |
| `00 00 00 0C` | 1 | 0..1 | 1 | 7-bit | `ENV_MODE` | Envelope Mode | 0: NO-SUS, 1: SUSTAIN |
| `00 00 00 0D` | 1 | 0..3 | 0 | 7-bit | `DELAY_MODE` | Delay Mode | 0: NORMAL, 1: HOLD, 2: KEYOFF-NORMAL, 3: KEYOFF-DECAY |
| `00 00 00 0E` | 1 | 0..1 | 0 | 7-bit | `DLY_TIME_SYNC` | Delay Time Sync Switch | 0: OFF, 1: ON |
| `00 00 00 0F` | 1 | 0..21 | 12 | 7-bit | `DLY_TIME_NOTE` | Delay Time (Note sync) | 1/64T..1/1 |
| `00 00 00 10` | 4 | 0..1023 | 0 | 4 nibbles | `DLY_TIME` | Delay Time (msec) | 0..1023 |
| `00 00 00 14` | 1 | 0..127 | 0 | 7-bit | `CHO_SEND` | Delay / Chorus Send Level | 0..127 |
| `00 00 00 15` | 1 | 0..127 | 0 | 7-bit | `REV_SEND` | Reverb Send Level | 0..127 |
| `00 00 00 16` | 1 | 0..1 | 1 | 7-bit | `RX_BEND` | Receive Pitch Bend | 0: OFF, 1: ON |
| `00 00 00 17` | 1 | 0..1 | 1 | 7-bit | `RX_EXPR` | Receive Expression | 0: OFF, 1: ON |
| `00 00 00 18` | 1 | 0..1 | 1 | 7-bit | `RX_HOLD` | Receive Hold-1 (Sustain)| 0: OFF, 1: ON |
| `00 00 00 19` | 1 | 0..1 | 0 | 7-bit | `REDAMP_SW` | Redamper Switch | 0: OFF, 1: ON |
| `00 00 00 1A` | 1 | 0..1 | 1 | 7-bit | `OUT_ASGN` | Output Assign | 0: DRY, 1: MFX |
| `00 00 00 1B` | 1 | 0..3 | 0 | 7-bit | `WAV_GTYPE` | Wave Group Type | 0: INT, 1: EXP, 2: SAMP, 3: MSAMP |
| `00 00 00 1C` | 4 | 0..16383 | 8 | 4 nibbles | `WAV_GID` | Wave Group ID | Bank number |
| `00 00 00 20` | 4 | 0..16383 | 0 | 4 nibbles | `WAV_NUM_L` | Wave Number Left / Mono | PCM Waveform Number |
| `00 00 00 24` | 4 | 0..16383 | 0 | 4 nibbles | `WAV_NUM_R` | Wave Number Right | PCM Waveform Number |
| `00 00 00 28` | 1 | 0..5 | 3 | 7-bit | `WAV_GAIN` | Wave Gain | -18, -12, -6, 0, +6, +12 dB |
| `00 00 00 29` | 1 | 0..1 | 0 | 7-bit | `FXM_SW` | Frequency Cross Mod Sw | 0: OFF, 1: ON |
| `00 00 00 2A` | 1 | 1..4 | 1 | 7-bit | `FXM_COLOR` | FXM Color | 1..4 |
| `00 00 00 2B` | 1 | 0..16 | 0 | 7-bit | `FXM_DEPTH` | FXM Depth | 0..16 |
| `00 00 00 2C` | 4 | -200..200 | 100 | 4 nibbles, +1024| `PIT_KF` | Pitch Keyfollow | -200..+200 |
| `00 00 00 30` | 1 | 0..100 | 0 | 7-bit | `SOFT_EQ_SENS` | Soft EQ Sens | 0..100 |
| `00 00 00 31` | 1 | 0..6 | 1 | 7-bit | `FILTER_TYPE` | TVF Filter Type | 0: OFF, 1: LPF, 2: BPF, 3: HPF, 4: PKG, 5: LPF2, 6: LPF3 |
| `00 00 00 32` | 4 | 0..1023 | 1023 | 4 nibbles | `CUTOFF` | TVF Cutoff Frequency | 0..1023 |
| `00 00 00 36` | 4 | -200..200 | 0 | 4 nibbles, +1024| `CUTOFF_KF` | TVF Cutoff Keyfollow | -200..+200 |
| `00 00 00 3A` | 1 | 0..7 | 1 | 7-bit | `CUTOFF_VCRV` | TVF Cutoff Velocity Curve| 0..7 |
| `00 00 00 3B` | 2 | -100..100 | 0 | 2 nibbles, +128| `CUTOFF_VSENS` | TVF Cutoff Velocity Sens | -100..+100 |
| `00 00 00 3D` | 4 | 0..1023 | 0 | 4 nibbles | `RESO` | TVF Resonance | 0..1023 |
| `00 00 00 41` | 2 | -100..100 | 0 | 2 nibbles, +128| `RESO_VSENS` | TVF Resonance Velo Sens | -100..+100 |
| `00 00 00 43` | 2 | -100..100 | 0 | 2 nibbles, +128| `BIAS_LEVEL` | Bias Level | -100..+100 |
| `00 00 00 45` | 1 | 0..127 | 60 | 7-bit | `BIAS_POS` | Bias Point Note | C-1..G9 |
| `00 00 00 46` | 1 | 0..3 | 3 | 7-bit | `BIAS_DIR` | Bias Direction | 0: LOWER, 1: UPPER, 2: LOWER&UPPER, 3: ALL |
| `00 00 00 47` | 1 | 0..7 | 1 | 7-bit | `LEVEL_VCRV` | TVA Level Velocity Curve | 0..7 |
| `00 00 00 48` | 2 | -100..100 | 0 | 2 nibbles, +128| `LEVEL_VSENS` | TVA Level Velocity Sens | -100..+100 |
| `00 00 00 4A` | 2 | -100..100 | 0 | 2 nibbles, +128| `PENV_TKF` | Pitch Env Time Keyfollow | -100..+100 |
| `00 00 00 4C` | 2 | -100..100 | 0 | 2 nibbles, +128| `FENV_TKF` | TVF Env Time Keyfollow | -100..+100 |
| `00 00 00 4E` | 2 | -100..100 | 0 | 2 nibbles, +128| `AENV_TKF` | TVA Env Time Keyfollow | -100..+100 |
| `00 00 00 50` | 2 | -100..100 | 10 | 2 nibbles, +128| `VIB_PIT_SENS` | Vibrato Pitch Sens | -100..+100 |
| `00 00 00 52` | 2 | -100..100 | 0 | 2 nibbles, +128| `VIB_CUT_SENS` | Vibrato Cutoff Sens | -100..+100 |
| `00 00 00 54` | 2 | -100..100 | 0 | 2 nibbles, +128| `VIB_AMP_SENS` | Vibrato Level Sens | -100..+100 |

#### Matrix Control 1..4 in PTL Block
Each of the 4 Matrix Control slots has 1 Source and 4 Destinations with dedicated Sensitivities:

| Offset | Parameter ID | Parameter Name | Range & Values |
|---|---|---|---|
| `00 00 00 56` | `MCTL1_SRC` | Matrix 1 Source | 0: OFF, 1..95: CC01..CC95, 96: BEND, 97: AFT, 98..101: SYS-CTRL1..4, 102: VEL, 103: KEYFOLLOW, 104: TEMPO, 105: LFO1, 106: LFO2, 107: PIT-ENV, 108: TVF-ENV, 109: TVA-ENV |
| `00 00 00 57` | `MCTL1_DST1` | Matrix 1 Destination 1 | 0: OFF, 1: PCH, 2: CUT, 3: RES, 4: LEV, 5: PAN, 6: DLY, 7: REV, 8..15: LFO Depths, 16..17: LFO Rates, 18..26: Env Times, 27: PMT, 28: FXM, 29..32: MFX-CTRL1..4, 33..48: Synth parameters (Appendix A) |
| `00 00 00 58` | `MCTL1_SENS1`| Matrix 1 Sens 1 | -63..+63 (Sent as 7-bit, +64) |
| `00 00 00 59` | `MCTL1_DST2` | Matrix 1 Destination 2 | (Same destinations as DST1) |
| `00 00 00 5A` | `MCTL1_SENS2`| Matrix 1 Sens 2 | -63..+63 (Sent as 7-bit, +64) |
| `00 00 00 5B` | `MCTL1_DST3` | Matrix 1 Destination 3 | (Same destinations as DST1) |
| `00 00 00 5C` | `MCTL1_SENS3`| Matrix 1 Sens 3 | -63..+63 (Sent as 7-bit, +64) |
| `00 00 00 5D` | `MCTL1_DST4` | Matrix 1 Destination 4 | (Same destinations as DST1) |
| `00 00 00 5E` | `MCTL1_SENS4`| Matrix 1 Sens 4 | -63..+63 (Sent as 7-bit, +64) |
| `00 00 00 5F` | `MCTL2_SRC` | Matrix 2 Source | Matrix 2 starts at 5F |
| `00 00 00 68` | `MCTL3_SRC` | Matrix 3 Source | Matrix 3 starts at 68 |
| `00 00 00 71` | `MCTL4_SRC` | Matrix 4 Source | Matrix 4 starts at 71 |
| `00 00 00 7A` | `DAMP_FREE` | Damper Free Note | 0: OFF, 1..127 |
| `00 00 00 7B` | `STEREO_WIDTH`| Stereo Width | 0..100 |
| `00 00 00 7C` | `STEREO_DETN` | Stereo Detune | -50..+50 cents (Sent as 7-bit, +64) |
| `00 00 00 7D` | `DF_DCY_OFST` | Damper Free Decay Offset | -100..+100 (Sent as 2 nibbles, +128) |
| `00 00 00 7F` | `TEMPO_SYNC` | Wave Tempo Sync | 0: OFF, 1: ON |

---

### 5.4 PENV: Pitch Envelope Block (`offset 00 00 24 00`, step `01 00`, len 45)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name |
|---|---|---|---|---|---|---|
| `00 00 00 00` | 2 | -100..100 | 0 | 2 nibbles, +128 | `DEPTH` | Pitch Env Depth |
| `00 00 00 02` | 2 | -100..100 | 0 | 2 nibbles, +128 | `VSENS` | Pitch Env Velocity Sens |
| `00 00 00 04` | 2 | -100..100 | 0 | 2 nibbles, +128 | `T1_VSENS` | Pitch Env T1 Velocity Sens |
| `00 00 00 06` | 2 | -100..100 | 0 | 2 nibbles, +128 | `T4_VSENS` | Pitch Env T4 Velocity Sens |
| `00 00 00 08` | 4 | 0..1023 | 0 | 4 nibbles | `T1` | Pitch Env Time 1 (Attack Time) |
| `00 00 00 0C` | 4 | 0..1023 | 0 | 4 nibbles | `T2` | Pitch Env Time 2 |
| `00 00 00 10` | 4 | 0..1023 | 0 | 4 nibbles | `T3` | Pitch Env Time 3 (Decay Time) |
| `00 00 00 14` | 4 | 0..1023 | 0 | 4 nibbles | `T4` | Pitch Env Time 4 (Release Time) |
| `00 00 00 18` | 4 | -511..511 | 0 | 4 nibbles, +1024 | `L0` | Pitch Env Level 0 |
| `00 00 00 1C` | 4 | -511..511 | 240 | 4 nibbles, +1024 | `L1` | Pitch Env Level 1 (Attack Level) |
| `00 00 00 20` | 4 | -511..511 | 240 | 4 nibbles, +1024 | `L2` | Pitch Env Level 2 |
| `00 00 00 24` | 4 | -511..511 | 240 | 4 nibbles, +1024 | `L3` | Pitch Env Level 3 (Sustain Level)|
| `00 00 00 28` | 4 | -511..511 | 0 | 4 nibbles, +1024 | `L4` | Pitch Env Level 4 (Release Level)|
| `00 00 00 2C` | 1 | 0..7 | 1 | 7-bit | `VCRV` | Pitch Env Velocity Curve |

---

### 5.5 FENV: TVF Filter Envelope Block (`offset 00 00 28 00`, step `01 00`, len 44)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name |
|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | -63..63 | 0 | 7-bit, +64 | `DEPTH` | Filter Env Depth |
| `00 00 00 01` | 1 | 0..7 | 1 | 7-bit | `VCRV` | Filter Env Velocity Curve |
| `00 00 00 02` | 2 | -100..100 | 0 | 2 nibbles, +128 | `VSENS` | Filter Env Velocity Sens |
| `00 00 00 04` | 2 | -100..100 | 0 | 2 nibbles, +128 | `T1_VSENS` | Filter Env T1 Velocity Sens |
| `00 00 00 06` | 2 | -100..100 | 0 | 2 nibbles, +128 | `T4_VSENS` | Filter Env T4 Velocity Sens |
| `00 00 00 08` | 4 | 0..1023 | 0 | 4 nibbles | `T1` | Filter Env Time 1 (Attack Time) |
| `00 00 00 0C` | 4 | 0..1023 | 0 | 4 nibbles | `T2` | Filter Env Time 2 |
| `00 00 00 10` | 4 | 0..1023 | 0 | 4 nibbles | `T3` | Filter Env Time 3 (Decay Time) |
| `00 00 00 14` | 4 | 0..1023 | 0 | 4 nibbles | `T4` | Filter Env Time 4 (Release Time)|
| `00 00 00 18` | 4 | 0..1023 | 0 | 4 nibbles | `L0` | Filter Env Level 0 |
| `00 00 00 1C` | 4 | 0..1023 | 1023 | 4 nibbles | `L1` | Filter Env Level 1 (Peak Level) |
| `00 00 00 20` | 4 | 0..1023 | 1023 | 4 nibbles | `L2` | Filter Env Level 2 |
| `00 00 00 24` | 4 | 0..1023 | 1023 | 4 nibbles | `L3` | Filter Env Level 3 (Sustain Level)|
| `00 00 00 28` | 4 | 0..1023 | 0 | 4 nibbles | `L4` | Filter Env Level 4 (Release Level)|

---

### 5.6 AENV: TVA Amp Envelope Block (`offset 00 00 2C 00`, step `01 00`, len 32)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name |
|---|---|---|---|---|---|---|
| `00 00 00 00` | 2 | -100..100 | 0 | 2 nibbles, +128 | `T1_VSENS` | Amp Env Time 1 Velocity Sens |
| `00 00 00 02` | 2 | -100..100 | 0 | 2 nibbles, +128 | `T4_VSENS` | Amp Env Time 4 Velocity Sens |
| `00 00 00 04` | 4 | 0..1023 | 0 | 4 nibbles | `T1` | Amp Env Time 1 (Attack Time) |
| `00 00 00 08` | 4 | 0..1023 | 30 | 4 nibbles | `T2` | Amp Env Time 2 |
| `00 00 00 0C` | 4 | 0..1023 | 400 | 4 nibbles | `T3` | Amp Env Time 3 (Decay Time) |
| `00 00 00 10` | 4 | 0..1023 | 400 | 4 nibbles | `T4` | Amp Env Time 4 (Release Time)|
| `00 00 00 14` | 4 | 0..1023 | 1023 | 4 nibbles | `L1` | Amp Env Level 1 (Peak Level) |
| `00 00 00 18` | 4 | 0..1023 | 1023 | 4 nibbles | `L2` | Amp Env Level 2 |
| `00 00 00 1C` | 4 | 0..1023 | 1023 | 4 nibbles | `L3` | Amp Env Level 3 (Sustain Level)|

---

### 5.7 LFO: Dual LFO Block (`offset 00 00 30 00`, step `02 00`, len 158)
Each Partial has two independent LFOs (LFO 1 starts at `+00`, LFO 2 starts at `+4F`):

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..10 | 1 | 7-bit | `LFO1_FORM` | Waveform | 0: SIN, 1: TRI, 2: SAW-UP, 3: SAW-DW, 4: SQR, 5: RND, 6: TRP, 7: S&H, 8: CHS, 9: VSIN, 10: STEP |
| `00 00 00 01` | 1 | 0..1 | 0 | 7-bit | `LFO1_RATE_SYNC`| Tempo Sync Switch | 0: OFF, 1: ON |
| `00 00 00 02` | 1 | 0..22 | 12 | 7-bit | `LFO1_RATE_NOTE`| Tempo Sync Note | 1/64T..4 bars (23 values, Appendix B) |
| `00 00 00 03` | 1 | 0..15 | 15 | 7-bit | `LFO1_STEP_MAX` | Step Sequencer Length | 1..16 steps |
| `00 00 00 04` | 4 | 0..1023 | 650 | 4 nibbles | `LFO1_RATE` | Rate (Hz) | 0..1023 |
| `00 00 00 08` | 2 | -100..100 | 0 | 2 nibbles, +128| `LFO1_OFST` | Offset | -100..+100 |
| `00 00 00 0A` | 1 | 0..127 | 0 | 7-bit | `LFO1_RATE_DETN`| Rate Detune | 0..127 |
| `00 00 00 0B` | 4 | 0..1023 | 0 | 4 nibbles | `LFO1_DELAY` | Delay Time | 0..1023 |
| `00 00 00 0F` | 2 | -100..100 | 0 | 2 nibbles, +128| `LFO1_DELAY_KF` | Delay Time Keyfollow | -100..+100 |
| `00 00 00 11` | 1 | 0..3 | 0 | 7-bit | `LFO1_FADE_MODE`| Fade Mode | 0: ON-IN, 1: ON-OUT, 2: OFF-IN, 3: OFF-OUT |
| `00 00 00 12` | 4 | 0..1023 | 0 | 4 nibbles | `LFO1_FADE` | Fade Time | 0..1023 |
| `00 00 00 16` | 1 | 0..1 | 0 | 7-bit | `LFO1_KEY_TRIG` | Key Trigger Switch | 0: OFF, 1: ON |
| `00 00 00 17` | 2 | -100..100 | 0 | 2 nibbles, +128| `LFO1_PIT_DEPTH`| Pitch LFO Depth | -100..+100 |
| `00 00 00 19` | 2 | -100..100 | 0 | 2 nibbles, +128| `LFO1_TVF_DEPTH`| Filter LFO Depth | -100..+100 |
| `00 00 00 1B` | 2 | -100..100 | 0 | 2 nibbles, +128| `LFO1_TVA_DEPTH`| Amp LFO Depth | -100..+100 |
| `00 00 00 1D` | 1 | -63..63 | 0 | 7-bit, +64 | `LFO1_PAN_DEPTH`| Pan LFO Depth | -63..+63 |
| `00 00 00 1E` | 1 | 0..3 | 0 | 7-bit | `LFO1_PHASE_POS`| Phase Position | 0, 90, 180, 270 deg |
| `00 00 00 1F` | 2 | -72..72 | 0 | 2 nibbles, +128| `LFO1_STEP_1` | Step 1 Value | -72..+72 semitones |
| *(Steps 2..16 span offsets `00 00 00 21` through `00 00 00 3D` in steps of 2 bytes)* |
| `00 00 00 3F` | 1 | 0..36 | 1 | 7-bit | `LFO1_STEP_CURVE_1`| Step Curve 1 | 0..36 Curve type |
| *(Curves 2..16 span offsets `00 00 00 40` through `00 00 00 4E` in steps of 1 byte)* |
| `00 00 00 4F` | 1 | 0..10 | 1 | 7-bit | `LFO2_FORM` | LFO 2 Waveform | (Same as LFO 1) |
| *(LFO 2 parameters repeat the exact identical sequence of offsets from `+4F` through `+11D`)* |

---

### 5.8 EQ: Partial 3-Band Parametric EQ Block (`offset 00 00 38 00`, step `01 00`, len 27)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 4 | -240..240 | 0 | 4 nibbles, +1024 | `LO_GAIN` | Low Gain | -24.0 .. +24.0 dB |
| `00 00 00 04` | 4 | -240..240 | 0 | 4 nibbles, +1024 | `MID_GAIN` | Mid Gain | -24.0 .. +24.0 dB |
| `00 00 00 08` | 4 | -240..240 | 0 | 4 nibbles, +1024 | `HI_GAIN` | High Gain | -24.0 .. +24.0 dB |
| `00 00 00 0C` | 4 | 20..16000 | 200 | 4 nibbles | `LO_FREQ` | Low Frequency | 20 .. 16000 Hz |
| `00 00 00 10` | 4 | 20..16000 | 1000| 4 nibbles | `MID_FREQ` | Mid Frequency | 20 .. 16000 Hz |
| `00 00 00 14` | 4 | 20..16000 | 2000| 4 nibbles | `HI_FREQ` | High Frequency | 20 .. 16000 Hz |
| `00 00 00 18` | 2 | 5..160 | 10 | 2 nibbles | `MID_Q` | Mid Q factor | 0.5 .. 16.0 |
| `00 00 00 1A` | 1 | 0..1 | 0 | 7-bit | `SW` | EQ Bypass Switch | 0: OFF, 1: ON |

---

### 5.9 SCMN: Synth Common Block (`offset 00 00 3C 00`, len 9)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..1 | 0 | 7-bit | `UNISON_SW` | Unison Switch | 0: OFF, 1: ON |
| `00 00 00 01` | 1 | 2..8 | 4 | 7-bit | `UNISON_SIZE` | Unison Voice Count | 2..8 voices |
| `00 00 00 02` | 1 | 0..100 | 20 | 7-bit | `UNISON_DETN` | Unison Detune Depth | 0..100 |
| `00 00 00 03` | 1 | 0..100 | 0 | 7-bit | `BEND_RANGE_FINE_UP`| Pitch Bend Fine Up | 0..100 cents |
| `00 00 00 04` | 1 | 0..100 | 0 | 7-bit | `BEND_RANGE_FINE_DW`| Pitch Bend Fine Down | 0..100 cents |
| `00 00 00 05` | 2 | 0..255 | 0 | 2 nibbles | `RND_PIT_VAL` | Pitch Drift Depth | 0..255 |
| `00 00 00 07` | 1 | 0..8 | 0 | 7-bit | `RND_PIT_NUM` | Pitch Drift Cycle Num| 0: FREE, 1..8 |
| `00 00 00 08` | 1 | 0..100 | 0 | 7-bit | `CONDITION` | Synth Condition (Aging)| 0..100 |

---

### 5.10 SPMT: Synth Structure Block (`offset 00 00 3D 00`, len 23)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..4 | 0 | 7-bit | `STRUCT12` | Structure Partial 1-2 | 0: OFF, 1: SYNC, 2: RING, 3: XMOD, 4: XMOD2 |
| `00 00 00 01` | 1 | 0..4 | 0 | 7-bit | `STRUCT34` | Structure Partial 3-4 | 0: OFF, 1: SYNC, 2: RING, 3: XMOD, 4: XMOD2 |
| `00 00 00 02` | 1 | 0..127 | 127 | 7-bit | `RING12_LEVEL` | Ring 1-2 Level | 0..127 |
| `00 00 00 03` | 1 | 0..127 | 127 | 7-bit | `RING34_LEVEL` | Ring 3-4 Level | 0..127 |
| `00 00 00 04` | 1 | 0..127 | 0 | 7-bit | `RING_OSC1_LEVEL`| Ring OSC1 Send Level | 0..127 |
| `00 00 00 05` | 1 | 0..127 | 0 | 7-bit | `RING_OSC2_LEVEL`| Ring OSC2 Send Level | 0..127 |
| `00 00 00 06` | 1 | 0..127 | 0 | 7-bit | `RING_OSC3_LEVEL`| Ring OSC3 Send Level | 0..127 |
| `00 00 00 07` | 1 | 0..127 | 0 | 7-bit | `RING_OSC4_LEVEL`| Ring OSC4 Send Level | 0..127 |
| `00 00 00 08` | 4 | 0..10800 | 1200| 4 nibbles | `XMOD12_DEPTH` | CrossMod 1-2 Depth | 0..10800 cents |
| `00 00 00 0C` | 4 | 0..10800 | 1200| 4 nibbles | `XMOD34_DEPTH` | CrossMod 3-4 Depth | 0..10800 cents |
| `00 00 00 10` | 1 | 0..127 | 127 | 7-bit | `XMOD_OSC1_LEVEL`| CrossMod OSC1 Level | 0..127 |
| `00 00 00 11` | 1 | 0..127 | 0 | 7-bit | `XMOD_OSC2_LEVEL`| CrossMod OSC2 Level | 0..127 |
| `00 00 00 12` | 1 | 0..127 | 127 | 7-bit | `XMOD_OSC3_LEVEL`| CrossMod OSC3 Level | 0..127 |
| `00 00 00 13` | 1 | 0..127 | 0 | 7-bit | `XMOD_OSC4_LEVEL`| CrossMod OSC4 Level | 0..127 |
| `00 00 00 14` | 1 | 0..1 | 1 | 7-bit | `PTL_PHS_LOCK` | Partial Phase Lock | 0: OFF, 1: ON |
| `00 00 00 15` | 1 | 0..127 | 100 | 7-bit | `XMOD2_12_DEPTH`| CrossMod2 1-2 Depth | 0..127 |
| `00 00 00 16` | 1 | 0..127 | 100 | 7-bit | `XMOD2_34_DEPTH`| CrossMod2 3-4 Depth | 0..127 |

---

### 5.11 SPTL: Synth Partial Block (`offset 00 00 3E 00`, step `01 00`, len 29)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..4 | 0 | 7-bit | `OSC_TYPE` | Oscillator Model | 0: PCM, 1: VA, 2: PCM-Sync, 3: SuperSAW, 4: Noise |
| `00 00 00 01` | 1 | 0..8 | 0 | 7-bit | `VA_FORM` | VA Waveform | 0: SAW, 1: SQR, 2: TRI, 3: SIN, 4: RAMP, 5: JUNO, 6: TRI2, 7: TRI3, 8: SIN2 |
| `00 00 00 02` | 4 | 0..16383 | 0 | 4 nibbles | `SYNC_WAV_NUM` | PCM-Sync Wave Number | Waveform Index |
| `00 00 00 06` | 1 | 0..127 | 64 | 7-bit | `PW` | Pulse Width | 0..127 |
| `00 00 00 07` | 1 | -63..63 | 0 | 7-bit, +64 | `PWM_DEPTH` | Pulse Width Mod Depth | -63..+63 |
| `00 00 00 08` | 1 | 0..127 | 64 | 7-bit | `SSAW_DETUNE` | SuperSAW Detune | 0..127 |
| `00 00 00 09` | 1 | 0..3 | 2 | 7-bit | `CLICK_TYPE` | VA Wave Click Type | 0: SOFT, 1: HARD, 2: NATURAL, 3: OFF |
| `00 00 00 0A` | 4 | 0..1023 | 0 | 4 nibbles | `HPF_CUTOFF` | High Pass Filter Cutoff | 0..1023 |
| `00 00 00 0E` | 1 | 0..1 | 0 | 7-bit | `FILTER_TYPE` | Filter Architecture | 0: TVF (Roland standard), 1: VCF (Vintage models) |
| `00 00 00 0F` | 1 | 0..2 | 0 | 7-bit | `FILTER_SLOPE` | Filter Slope | 0: -12 dB/oct, 1: -18 dB/oct, 2: -24 dB/oct |
| `00 00 00 10` | 1 | 0..1 | 0 | 7-bit | `ADSR_ENV_SW` | Simplified ADSR Env Switch| 0: OFF (Multi-step), 1: ON (Classic ADSR) |
| `00 00 00 11` | 1 | 0..127 | 64 | 7-bit | `FAT` | Filter Resonance Fatness | 0..127 |
| `00 00 00 12` | 1 | 0..3 | 0 | 7-bit | `VCF_TYPE` | Vintage VCF Model | 0: FLAT, 1: TYPE-JP (Jupiter), 2: TYPE-M (Moog), 3: TYPE-P (Prophet) |
| `00 00 00 13` | 2 | 0..255 | 255 | 2 nibbles | `OSC_ATT` | Oscillator Attenuator | 0..255 |
| `00 00 00 15` | 1 | 0..127 | 60 | 7-bit | `CUTOFF_KF_BP` | Cutoff Keyfollow Base Pt | C-1..G9 |
| `00 00 00 16` | 1 | 0..1 | 0 | 7-bit | `VA_INVERT_SW` | VA Waveform Invert Switch| 0: OFF, 1: ON |
| `00 00 00 17` | 1 | -63..63 | 0 | 7-bit, +64 | `FENV_FINE_DEPTH`| TVF Env Fine Depth | -63..+63 |
| `00 00 00 18` | 1 | 0..1 | 0 | 7-bit | `PENV_LFO_TRIG_SW`| Pitch Env LFO Retrigger | 0: OFF, 1: ON |
| `00 00 00 19` | 1 | 0..1 | 0 | 7-bit | `FENV_LFO_TRIG_SW`| Filter Env LFO Retrigger | 0: OFF, 1: ON |
| `00 00 00 1A` | 1 | 0..1 | 0 | 7-bit | `AENV_LFO_TRIG_SW`| Amp Env LFO Retrigger | 0: OFF, 1: ON |
| `00 00 00 1B` | 1 | 0..120 | 0 | 7-bit | `PITCH_DOWN_DEPTH`| Pitch Down Drop Depth | 0..120 |
| `00 00 00 1C` | 1 | 0..127 | 0 | 7-bit | `VCF_GC` | VCF Gain Correction | 0..127 |

---

## 6. Drum Kit ZEN-Core Parameter Specifications

### 6.1 KCMN: Drum Kit Common (`offset 00 00 00 00`, len 25)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 16 | — | — | text | `NAME` | Drum Kit Name | 16 ASCII characters |
| `00 00 00 10` | 4 | 0..65535 | 0 | 4 nibbles | `PHRASE` | Pattern Phrase Number | 0..65535 |
| `00 00 00 14` | 1 | 0..127 | 127 | 7-bit | `LEVEL` | Kit Master Level | 0..127 |
| `00 00 00 15` | 2 | 1..200 | 100 | 2 nibbles | `PHRASE_VEL_RATE` | Phrase Velocity Rate | 1..200% |
| `00 00 00 17` | 2 | -100..100 | 0 | 2 nibbles, +128| `PHRASE_VEL_SHIFT`| Phrase Velocity Shift | -100..+100 |

---

### 6.2 KCMP: Drum Kit Compressor Blocks 1..6 (`offset 00 00 10 00`, step `01 00`, len 8)
6 individual compressors per drum kit. Drum partials route to Comp 1..6 via `OUT_ASGN`.

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..1 | 0 | 7-bit | `SW` | Compressor Bypass Switch | 0: OFF, 1: ON |
| `00 00 00 01` | 1 | 0..100 | 0 | 7-bit | `ATTCK` | Attack Time | 0.1 .. 100 ms |
| `00 00 00 02` | 1 | 0..99 | 0 | 7-bit | `RELEASE` | Release Time | 10 .. 1000 ms |
| `00 00 00 03` | 1 | -60..0 | 0 | 7-bit, +64 | `THRESHOLD` | Threshold Level | -60 .. 0 dB |
| `00 00 00 04` | 1 | 0..7 | 0 | 7-bit | `RATIO` | Compression Ratio | 0: 1:1, 1: 2:1, 2: 3:1, 3: 4:1, 4: 8:1, 5: 16:1, 6: 32:1, 7: INF:1 |
| `00 00 00 05` | 1 | 0..30 | 0 | 7-bit | `KNEE` | Knee Width | 0 .. 30 dB |
| `00 00 00 06` | 1 | -48..48 | 0 | 7-bit, +64 | `POSTGAIN` | Post Gain (Makeup) | -48 .. +48 dB |
| `00 00 00 07` | 1 | 0..1 | 1 | 7-bit | `OUT_ASGN` | Compressor Routing | 0: DRY, 1: MFX |

---

### 6.3 KPTL: Drum Kit Partial Block (`offset 00 00 16 00`, step `01 00`, len 27)
Repeats for all 88 keys ($21 \dots 108$). Contains the instrument link and key offsets:

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name | Values / Units |
|---|---|---|---|---|---|---|---|
| `00 00 00 00` | 4 | 0..32768 | 0 | 4 nibbles | `INST_NUM` | Instrument Number | Instrument Preset Index |
| `00 00 00 04` | 1 | 0..2 | 0 | 7-bit | `INST_GTYPE` | Instrument Bank Type | 0: PRESET, 1: USER, 2: EXP |
| `00 00 00 05` | 4 | 0..16383 | 0 | 4 nibbles | `INST_GID` | Instrument Group ID | Bank Category Index |
| `00 00 00 09` | 1 | 0..127 | 127 | 7-bit | `LEVEL` | Pad Level | 0..127 |
| `00 00 00 0A` | 1 | -64..63 | 0 | 7-bit, +64 | `PAN` | Pad Pan | L64..C..R63 |
| `00 00 00 0B` | 1 | 0..127 | 127 | 7-bit | `CHO_SEND` | Delay / Chorus Send Level | 0..127 |
| `00 00 00 0C` | 1 | 0..127 | 127 | 7-bit | `REV_SEND` | Reverb Send Level | 0..127 |
| `00 00 00 0D` | 1 | 0..31 | 0 | 7-bit | `MUTE_GRP` | Mute Group | 0: OFF, 1..31 |
| `00 00 00 0E` | 1 | 0..7 | 1 | 7-bit | `OUT_ASGN` | Output Destination | 0: DRY, 1: MFX, 2..7: COMP 1..6 |
| `00 00 00 0F` | 1 | -24..24 | 0 | 7-bit, +64 | `KEY_OFST` | Key Pitch Offset | -24 .. +24 Semitones |
| `00 00 00 10` | 1 | -50..50 | 0 | 7-bit, +64 | `PIT_FINE_OFST` | Fine Tune Offset | -50 .. +50 Cents |
| `00 00 00 11` | 2 | -100..100 | 0 | 2 nibbles, +128| `CUTOFF_OFST` | TVF Cutoff Offset | -100 .. +100 |
| `00 00 00 13` | 2 | -100..100 | 0 | 2 nibbles, +128| `RESO_OFST` | TVF Resonance Offset | -100 .. +100 |
| `00 00 00 15` | 2 | -100..100 | 0 | 2 nibbles, +128| `TVA_ATK_OFST` | TVA Attack Time Offset | -100 .. +100 |
| `00 00 00 17` | 2 | -100..100 | 0 | 2 nibbles, +128| `TVA_DCY_OFST` | TVA Decay Time Offset | -100 .. +100 |
| `00 00 00 19` | 2 | -100..100 | 0 | 2 nibbles, +128| `TVA_REL_OFST` | TVA Release Time Offset | -100 .. +100 |

---

### 6.4 KEQ: Drum Key EQ Block (`offset 00 00 6E 00`, step `01 00`, len 27)
Repeats for each of the 88 drum keys. Follows the exact parameter structure of the Tone Partial EQ table (Section 5.8).

---

## 7. Multi-Effects (MFX) Processor Reference

The MFX processor is embedded at offset `00 00 01 00` within both Tone and Drum Kit active slots.

### 7.1 MFX Core Configuration Block (`offset 00 00 01 00`, len 144)

| Offset | Size | Range | Init | Sent as | Parameter ID | Parameter Name |
|---|---|---|---|---|---|---|
| `00 00 00 00` | 1 | 0..90 | 0 | 7-bit | `mfxType` | MFX Type (0: Thru, 1..90) |
| `00 00 00 01` | 1 | 0..1 | 1 | 7-bit | `mfxSwitch` | MFX Bypass Switch (0: OFF, 1: ON) |
| `00 00 00 02` | 1 | 0..127 | 127 | 7-bit | `choSend` | MFX Delay/Chorus Send Level |
| `00 00 00 03` | 1 | 0..127 | 127 | 7-bit | `revSend` | MFX Reverb Send Level |
| `00 00 00 04` | 1 | 0..100 | 0 | 7-bit | `ctrlSrc1` | MFX Control Source 1 |
| `00 00 00 05` | 1 | -63..63 | 0 | 7-bit, +64 | `ctrlSens1` | MFX Control Sens 1 |
| `00 00 00 06` | 1 | 0..100 | 0 | 7-bit | `ctrlSrc2` | MFX Control Source 2 |
| `00 00 00 07` | 1 | -63..63 | 0 | 7-bit, +64 | `ctrlSens2` | MFX Control Sens 2 |
| `00 00 00 08` | 1 | 0..100 | 0 | 7-bit | `ctrlSrc3` | MFX Control Source 3 |
| `00 00 00 09` | 1 | -63..63 | 0 | 7-bit, +64 | `ctrlSens3` | MFX Control Sens 3 |
| `00 00 00 0A` | 1 | 0..100 | 0 | 7-bit | `ctrlSrc4` | MFX Control Source 4 |
| `00 00 00 0B` | 1 | -63..63 | 0 | 7-bit, +64 | `ctrlSens4` | MFX Control Sens 4 |
| `00 00 00 0C` | 1 | 0..11 | 0 | 7-bit | `ctrlAsgn_1` | MFX Control Destination 1 |
| `00 00 00 0D` | 1 | 0..11 | 0 | 7-bit | `ctrlAsgn_2` | MFX Control Destination 2 |
| `00 00 00 0E` | 1 | 0..11 | 0 | 7-bit | `ctrlAsgn_3` | MFX Control Destination 3 |
| `00 00 00 0F` | 1 | 0..11 | 0 | 7-bit | `ctrlAsgn_4` | MFX Control Destination 4 |
| `00 00 00 10` | 4 | -20000..20000 | 0 | 4 nibbles, +32768 | `param_1` | Parameter Slot 1 |
| `00 00 00 14` | 4 | -20000..20000 | 0 | 4 nibbles, +32768 | `param_2` | Parameter Slot 2 |
| *(Parameter slots `param_3`..`param_32` span offsets `00 00 00 18` through `00 00 01 0C` in 4-byte steps)* |

### 7.2 Complete MFX Types (0 Through 90) & Parameter Slots

Every parameter slot is sent as **4 nibbles with +32768 offset**. Decimals are scaled on the wire (Hz $\times 100$, ms $\times 10$, dB $\times 10$ or $\times 100$).

> [!CRITICAL]
> **The 300 ms MFX Reset Rule**: When changing `mfxType` (offset `00 00 00 00`), the MC-101 firmware re-initializes and overwrites all 32 parameter slots with default values within approximately 250 ms. **Your application MUST wait at least 300 ms after writing `mfxType` before sending any custom `param_1`..`param_32` values**, otherwise your writes will be overwritten!

#### Selected Core MFX Type Slot Definitions

- **0 Thru**: No parameters.
- **1 Equalizer**: Low Freq (1), Low Gain (2), Mid1 Freq (3), Mid1 Gain (4), Mid1 Q (5), Mid2 Freq (6), Mid2 Gain (7), Mid2 Q (8), High Freq (9), High Gain (10), Level (11).
- **2 Spectrum**: Band 1..8 Gain (1..8), Q (9), Level (10).
- **3 Isolator**: Boost/Cut Low/Mid/High (1..3), AntiPhase Low Sw/Level (4..5), AntiPhase Mid Sw/Level (6..7), Low Boost Sw/Level (8..9), Level (10).
- **4 Low Boost**: Boost Freq (1), Boost Gain (2), Boost Width (3), Low Gain (4), High Gain (5), Level (6).
- **5 Super Filter**: Filter Type (1), Slope (2), Cutoff (3), Resonance (4), Gain (5), Mod Sw (6), Mod Wave (7), Rate Sync (8), Rate Hz (9), Rate Note (10), Depth (11), Attack (12), Level (13).
- **6 Step Filter**: Steps 1..16 (1..16), Rate Sync (17), Rate Hz (18), Rate Note (19), Attack (20), Filter Type (21), Slope (22), Resonance (23), Gain (24), Level (25).
- **7 Enhancer**: Sens (1), Mix (2), Low Gain (3), High Gain (4), Level (5).
- **8 Auto Wah**: Filter Type (1), Manual (2), Peak (3), Sens (4), Polarity (5), Rate Sync (6), Rate Hz (7), Rate Note (8), Depth (9), Phase (10), Low Gain (11), High Gain (12), Level (13).
- **9 Humanizer**: Drive Sw (1), Drive (2), Vowel 1..2 (3..4), Rate Sync (5), Rate Hz (6), Rate Note (7), Depth (8), Input Sync Sw (9), Threshold (10), Manual (11), Low/High Gain (12..13), Pan (14), Level (15).
- **10 Speaker Sim**: Speaker Type (1), Mic Setting (2), Mic Level (3), Direct Level (4), Level (5).
- **11 Phaser 1**: Mode (1), Manual (2), Rate Sync/Hz/Note (3..5), Depth (6), Polarity (7), Reso (8), Cross FB (9), Mix (10), Low/High Gain (11..12), Level (13).
- **12 Phaser 2**: Rate (1), Color (2), Low Gain (3), High Gain (4), Level (5).
- **13 Phaser 3**: Speed (1), Depth (2), Low Gain (3), High Gain (4), Level (5).
- **14 Step Phaser**: Mode (1), Manual (2), Rate Sync/Hz/Note (3..5), Depth (6), Polarity (7), Reso (8), Cross FB (9), Step Rate Sync/Hz/Note (10..12), Mix (13), Low/High Gain (14..15), Level (16).
- **15 Multi Stage Phaser**: Mode (1), Manual (2), Rate Sync/Hz/Note (3..5), Depth (6), Reso (7), Pan (8), Low Gain (9), Level (10).
- **16 Infinite Phaser**: Mode (1), Speed (2), Reso (3), Mix (4), Pan (5), Low/High Gain (6..7), Level (8).
- **17 Ring Modulator**: Frequency (1), Sens (2), Polarity (3), Low/High Gain (4..5), Balance (6), Level (7).
- **18 Tremolo**: Mod Wave (1), Rate Sync/Hz/Note (2..4), Depth (5), Low/High Gain (6..7), Level (8).
- **19 Auto Pan**: Mod Wave (1), Rate Sync/Hz/Note (2..4), Depth (5), Low/High Gain (6..7), Level (8).
- **20 Slicer**: Steps 1..16 (1..16), Rate Sync/Hz/Note (17..19), Attack (20), Input Sync Sw/Thresh (21..22), Mode (23), Shuffle (24), Level (25).
- **21 Rotary**: Speed (1), Woofer Slow/Fast (2..3), Woofer Accel/Level (4..5), Tweeter Slow/Fast (6..7), Tweeter Accel/Level (8..9), Separation (10), Level (11).
- **22 VK Rotary**: Speed (1), Brake (2), Woofer Slow/Fast/Trans/Level (3..7), Tweeter Slow/Fast/Trans/Level (8..12), Spread (13), Low/High Gain (14..15), Level (16), OD Sw/Gain/Drive/Level (17..20).
- **23 Chorus**: Filter Type (1), Cutoff (2), Pre Delay (3), Rate Sync/Hz/Note (4..6), Depth (7), Phase (8), Low/High Gain (9..10), Balance (11), Level (12).
- **24 Flanger**: Filter Type (1), Cutoff (2), Pre Delay (3), Rate Sync/Hz/Note (4..6), Depth (7), Phase (8), Feedback (9), Low/High Gain (10..11), Balance (12), Level (13).
- **25 Step Flanger**: Like Flanger + Step Rate Sync/Hz/Note (10..12).
- **26 Hexa-Chorus**: Pre Delay (1), Rate Sync/Hz/Note (2..4), Depth (5), Pre Delay Dev (6), Depth Dev (7), Pan Dev (8), Balance (9), Level (10).
- **27 Tremolo Chorus**: Pre Delay (1), Chorus Rate/Depth (2..5), Tremolo Rate/Sep/Phase (6..10), Balance (11), Level (12).
- **28 Space-D**: Pre Delay (1), Rate Sync/Hz/Note (2..4), Depth (5), Phase (6), Low/High Gain (7..8), Balance (9), Level (10).
- **29 Overdrive**: Drive (1), Tone (2), Amp Sw/Type (3..4), Low/High Gain (5..6), Pan (7), Level (8).
- **30 Distortion**: Drive (1), Tone (2), Amp Sw/Type (3..4), Low/High Gain (5..6), Pan (7), Level (8).
- **31 T-Scream**: Distortion (1), Tone (2), Level (3).
- **32 Guitar Amp Simulator**: PreAmp Sw/Type/Vol/Master/Gain/Bass/Mid/Treb/Pres/Bright (1..10), Speaker Sw/Type/Mic/MicLev/DirectLev (11..15), Pan (16), Level (17).
- **33 Compressor**: Attack (1), Release (2), Threshold (3), Knee (4), Ratio (5), Post Gain (6), Level (7).
- **34 Limiter**: Release (1), Threshold (2), Ratio (3), Post Gain (4), Low/High Gain (5..6), Level (7).
- **35 Sustainer**: Sustain (1), Attack (2), Release (3), Post Gain (4), Low/High Gain (5..6), Level (7).
- **36 Gate**: Threshold (1), Mode (2), Attack (3), Hold (4), Release (5), Balance (6), Level (7).
- **37 Delay**: Left/Right Delay Time Sync/ms/note (1..6), Left/Right Phase (7..8), Feedback Mode/Amount (9..10), HF Damp (11), Low/High Gain (12..13), Balance (14), Level (15).
- **38 Modulation Delay**: Delay + Modulation Rate/Depth/Phase (10..14).
- **39 3Tap Pan Delay**: Left/Right/Center Delay Times, Center FB, HF Damp, Left/Right/Center Levels, Tone & Level.
- **40 4Tap Pan Delay**: 4 Delays with Sync/ms/note (1..12), Delay 1 FB (13), HF Damp (14), Levels 1..4 (15..18), Low/High Gain, Balance, Level.
- **41 Multi Tap Delay**: 4 Delays with Pans (15..18) and Levels (19..22).
- **42 Reverse Delay**: Rev Delay params + 3 forward delay taps.
- **43 Time Ctrl Delay**: Delay Time, Acceleration (4), Feedback (5), HF Damp (6), Tone & Level.
- **44 Tape Echo**: Mode (1), Repeat Rate (2), Intensity (3), Bass/Treble (4..5), Head S/M/L Pan (6..8), Distortion (9), W/F Rate/Depth (10..11), Echo/Direct Level (12..13), Level (14).
- **45 LOFI Compress**: Pre/LoFi/Post Filter, Cutoff, Tone, Balance, Level.
- **46 Bit Crusher**: Sample Rate (1), Bit Down (2), Filter (3), Low/High Gain (4..5), Level (6).
- **47 Pitch Shifter**: Coarse (1), Fine (2), Delay Sync/ms/note (3..5), Feedback (6), Low/High Gain (7..8), Balance (9), Level (10).
- **48 2Voice Pitch Shifter**: 2 independent pitch voices with Coarse/Fine/Delay/FB/Pan/Level.
- **49..71 Combinations**: Overdrive/Distortion/AmpSim $\rightarrow$ Chorus/Flanger/Delay.
- **72 CE-1**: Boss CE-1 Chorus Ensemble emulation.
- **73 SBF-325**: Stereo Flanger rack unit emulation.
- **74 SDD-320**: Roland Dimension D emulation (Modes 1..4, combinations).
- **75 2Tap Pan Delay**: 2 independent taps with panning.
- **76 Transient**: Attack (1), Release (2), Output Gain (3), Sense (4), Level (5).
- **77 Mid-Side EQ**: Independent 4-band Mid and Side parametric EQs.
- **78 Mid-Side Compressor**: Independent Mid and Side compressors.
- **79 Tone Fattener**: Odd Harmonics Level (1), Even Harmonics Level (2), Level (3).
- **80 Mid-Side Delay**: Independent Mid and Side stereo delays.
- **81 RD EPAmpSim**: Roland RD Electric Piano Amp Simulator with Tremolo & Speaker emulations.
- **82 DJFX Looper**: Length (1), Speed (2), Loop Sw (3), Level (4).
- **83 BPM Looper**: Length, Rate Sync/Hz/note, Timing, Loop Mode.
- **84 Saturator**: Multi-stage Saturation with Pre/Post filters, Drive, Makeup, Balance.
- **85 Warm Saturator**: Warm tube style saturation with multiband EQ.
- **86 Fuzz**: Drive, Tone, Level.
- **87 JUNO-106 Chorus**: Modes I, II, I+II, JX I, JX II, Noise Level, Balance, Level.
- **88 Multi Mode Filter**: LPF/HPF/BPF with Tone, Color, Slope, Gain, Level.
- **89 HMS Distortion**: Distortion, Level.
- **90 Phaser 100**: Rate Sync/Hz/note, Duty, Min, Max, Manual Sw/Val, Reso, Mix, Level.

---

## 8. Analog-Model (AX) & Mixer Offset Parameters

In addition to the core ZEN-Core partial blocks, the MC-101 firmware exposes runtime mixer offsets and analog-modeling extensions (mapped in the Benis67 controller implementation):

### 8.1 Per-Track Mixer Offsets (`MC_` Block)
These offsets allow modifying track parameters without modifying the saved Tone/Drum kit data:

| Parameter Name | Target Function | Wire Encoding | Notes |
|---|---|---|---|
| `MC_Level_Offset` | Track Output Level Offset | `7-bit` | Offsets tone/kit level |
| `MC_Cutoff_Offset` | Master Track Filter Cutoff Offset | `2 nibbles, +128` | Positive/Negative offset |
| `MC_A_Offset` | Master Track Attack Time Offset | `2 nibbles, +128` | Modifies all partial attack times |
| `MC_Ctrlr1_Offset`| Track Sound Macro Knob 1 | `7-bit` | Maps to the physical Sound knob |
| `MC_RevSend_` | Track Master Reverb Send Offset | `7-bit` | Send level to master reverb |
| `MC_DelaySend_` | Track Master Delay Send Offset | `7-bit` | Send level to master delay |
| `MC_Color` | Track FX Color Knob | `7-bit` | Controls track multi-filter / FX |

### 8.2 Analog-Model ("AX") Extensions
Used when a Tone uses vintage analog model behaviors:
- `AX_PartLevel`: Extended part attenuation.
- `AX_PortTime_Prg`: Programmable portamento curve profile.
- `AX_KeyRangeLower` / `AX_KeyRangeUpper`: Global split points.

---

## 9. Performance Features & Non-SysEx Mappings

It is vital not to confuse SysEx parameters with normal MIDI control messages:

1. **Scatter Pad Triggering**:
   - Scatter uses standard **MIDI Note On / Note Off messages on MIDI Channel 13**.
   - Scatter pads 1 through 16 correspond to **MIDI Notes 60 to 75** (Middle C upwards).
   - Hold duration controls the length of the scatter effect. Send Note-Off when released.
2. **Preset Performance CCs**:
   - CC messages sent on the track's basic channel (Channels 1 to 4) control live macro performance parameters (Cutoff CC74, Resonance CC71, Pan CC10, Volume CC7, Reverb Send CC91, Delay Send CC92).
3. **Transport**:
   - Play/Pause/Stop use standard MIDI Realtime single-byte messages: Start (`0xFA`), Stop (`0xFC`), Clock (`0xF8`).

---

## 10. Known Quirks, Hardware Bugs & Limitations

### 10.1 The Returned-Address Bug in DT1 Replies
The MC-101 and MC-707 hardware contains a documented firmware bug when replying to `RQ1` read requests: **the address returned in the DT1 reply packet is corrupt**.

#### Cause
The MC-101 computes the internal 32-bit linear address, then packs it as 8-bit bytes masked with `0x7F`, rather than converting back to Roland 7-bit septet notation:

$$L = (b_1 \ll 21) \mid (b_2 \ll 14) \mid (b_3 \ll 7) \mid b_4$$
$$\text{Returned Address} = \left[(L \gg 24) \& 0\text{x}7\text{F},\; (L \gg 16) \& 0\text{x}7\text{F},\; (L \gg 8) \& 0\text{x}7\text{F},\; L \& 0\text{x}7\text{F}\right]$$

#### Worked Example
Requesting address `30 00 00 00`:
- Linear address $L = 0\text{x}06000000$
- Returned address in DT1 reply: `06 00 00 00` (completely different from `30 00 00 00`!)

#### Consequences & Solution
- The transform is **lossy** (e.g. addresses with `0x80` and `0x00` in linear byte 0 both mask to `0x00`).
- **Never key your response parsers or reassembly buffers on the returned address in a DT1 reply.**
- **Solution**: Match incoming DT1 replies strictly to outstanding RQ1 requests using a strict **FIFO Queue** (request order).

---

### 10.2 Confirmed Hard Limitation: Drum Inst Layer is Unreachable via SysEx
On the MC-101, **the per-pad Drum Instrument layer (`Drum Inst`) cannot be edited over SysEx.**

#### What is Missing
- **Pad Assign Type** (MULTI vs SINGLE)
- **Pad Envelope Mode** (SUSTAIN vs NO-SUS for drum pads)
- **Inst Waveform / Sample Links** & WMT Velocity Splits
- **Inst-level Envelopes** (Pitch, Filter, Amp)

#### Disambiguation: The Two "Envelope Modes"
- **Tone Partial Envelope Mode** (`ENV_MODE` at `PTL` offset `00 00 00 0C`) **IS reachable** and works perfectly.
- **Drum Pad Instrument Envelope Mode** is **NOT reachable**.

#### Proof & Evidence
1. **Full Address Sweep**: A complete sweep of all 98,512 responding blocks found no Drum Inst memory region.
2. **Region `38` Silence**: On the MV-1/Fantom, `ClipRhymInstSet` lives at `38 00 00 00`. Probing `38 0B 00 00` through `38 0B 7F 00` on the MC-101 returned **0 replies out of 128 requests**.
3. **Project File Examination**: The `.mpj` file on the SD card stores an array of 11,968 Inst records (216 bytes each), but these are not exposed to the SysEx router.
4. **Offline Workaround**: Drum pad Assign Type and sample configurations can only be altered by modifying the project `.mpj` file offline on the SD card.

---

## 11. Tactics to Prevent Freezing & Buffer Overruns

The MC-101 has a low-power microcontroller managing MIDI UART I/O and ZEN-Core parameter updates. Flooding the device with SysEx packets without flow control causes **MIDI buffer overflow, dropped messages, audio glitches, and total OS lockups**.

Follow these strict timing and rate-limiting rules:

### 1. Inter-Message Rate Limiting (DT1 Writes)
- **Individual Parameter Writes**: When sending back-to-back DT1 parameter updates (e.g., sweeping a knob or sending fader banks), insert a **mandatory pause of 10 to 20 ms** between messages:
  $$\Delta t_{\text{DT1}} \ge 15\text{ ms}$$
- **Block Writes**: When transmitting large blocks (e.g., 64 or 128 bytes), allow **30 to 50 ms** after transmission for the unit to copy the buffer to DSP RAM.

### 2. Request Pacing (RQ1 Reads)
- **Sequential Requests Only**: **Never issue concurrent/pipelined RQ1 requests.** Wait for the DT1 reply packet to arrive before issuing the next RQ1.
- **Timeout Window**: Set your read timeout to at least **200 ms** (recommended: **600 ms** to accommodate garbage collection / flash access outliers).
- **Chunk Size Limit**: Even though RQ1 accepts larger requests, limit requests to **128 bytes** (`00 00 01 00`) per packet to prevent input buffer saturation.

### 3. The MFX Switch Rule
- **Mandatory 300 ms Guard Time**: Immediately after transmitting a write to `mfxType` (`offset 00 00 01 00`), pause your transmit thread for **at least 300 ms** before writing to `param_1`..`param_32`.

### 4. Batching vs Single-Byte Writes
- When initializing an entire partial or synth patch, sending two 64-byte block writes with a 40 ms pause is much safer and faster than sending 128 individual 1-byte DT1 writes (which would require $128 \times 15\text{ ms} = 1.92\text{ seconds}$).

---

## 12. Verification & Probing Methodology

When discovering new parameters or verifying uncharted addresses on the MC-101, use the **Four-Pass Differential Verification Technique**:

```
Pass 1: Capture Baseline  (RQ1 target address block)
           ↓
Pass 2: Noise Check       (RQ1 target address block with NO controls touched)
           ↓ (Ensure 0 bytes changed; eliminates internal clock/LFO drifting noise)
Pass 3: Modify Target     (Turn 1 knob on MC-101 front panel, then RQ1 capture)
           ↓ (Byte that changed is candidate parameter)
Pass 4: Revert Target     (Return knob to original position, then RQ1 capture)
           ↓ (Confirm byte returns to exact baseline value)
Match Confirmed!
```

---

## Appendix A. Matrix Control Destination Map

Destination indices $0 \dots 48$ for `MCTL1_DST1` through `MCTL4_DST4`:

| Index | Symbol | Parameter Destination | Index | Symbol | Parameter Destination |
|---|---|---|---|---|---|
| `0` | `OFF` | Off / None | `25` | `TVA-DCY` | TVA Envelope Decay Time |
| `1` | `PCH` | Pitch | `26` | `TVA-REL` | TVA Envelope Release Time |
| `2` | `CUT` | TVF Filter Cutoff | `27` | `PMT` | Partial Level / Mute |
| `3` | `RES` | TVF Resonance | `28` | `FXM` | Frequency Cross Modulation |
| `4` | `LEV` | TVA Partial Level | `29` | `MFX-CTRL1`| MFX Control 1 |
| `5` | `PAN` | Partial Pan | `30` | `MFX-CTRL2`| MFX Control 2 |
| `6` | `DLY` | Delay Send Level | `31` | `MFX-CTRL3`| MFX Control 3 |
| `7` | `REV` | Reverb Send Level | `32` | `MFX-CTRL4`| MFX Control 4 |
| `8` | `PIT-LFO1`| Pitch LFO 1 Depth | `33` | `PW` | Pulse Width |
| `9` | `PIT-LFO2`| Pitch LFO 2 Depth | `34` | `PWM` | Pulse Width Modulation Depth |
| `10`| `TVF-LFO1`| Filter LFO 1 Depth | `35` | `FAT` | Filter Resonance Fat |
| `11`| `TVF-LFO2`| Filter LFO 2 Depth | `36` | `XMOD` | Cross Modulation Depth |
| `12`| `TVA-LFO1`| Amp LFO 1 Depth | `37` | `LFO1_STEP`| LFO 1 Step Rate |
| `13`| `TVA-LFO2`| Amp LFO 2 Depth | `38` | `LFO2_STEP`| LFO 2 Step Rate |
| `14`| `PAN-LFO1`| Pan LFO 1 Depth | `39` | `SSAW-DETN`| SuperSAW Detune Depth |
| `15`| `PAN-LFO2`| Pan LFO 2 Depth | `40` | `PIT_DEPTH`| Pitch Envelope Depth |
| `16`| `LFO1-RATE`| LFO 1 Rate Frequency | `41` | `TVF-DEPTH`| Filter Envelope Depth |
| `17`| `LFO2-RATE`| LFO 2 Rate Frequency | `42` | `TVA-DEPTH`| TVA Level Sensitivity |
| `18`| `PIT-ATK` | Pitch Envelope Attack Time| `43` | `XMOD2` | Cross Modulation 2 Depth |
| `19`| `PIT-DCY` | Pitch Envelope Decay Time | `44` | `ATT` | Oscillator Attenuator |
| `20`| `PIT-REL` | Pitch Envelope Release Time| `45` | `RING-OSC1`| Ring Modulator OSC 1 Send Level |
| `21`| `TVF-ATK` | TVF Envelope Attack Time | `46` | `RING-OSC2`| Ring Modulator OSC 2 Send Level |
| `22`| `TVF-DCY` | TVF Envelope Decay Time | `47` | `XMOD-OSC1`| CrossMod OSC 1 Send Level |
| `23`| `TVF-REL` | TVF Envelope Release Time| `48` | `XMOD-OSC2`| CrossMod OSC 2 Send Level |
| `24`| `TVA-ATK` | TVA Envelope Attack Time | | | |

---

## Appendix B. Value & Enumeration Conversion Tables

### B.1 LFO Rate Note Table (0 to 22)
| Value | Musical Note Sync | Value | Musical Note Sync | Value | Musical Note Sync |
|---|---|---|---|---|---|
| `0` | 1/64T (Triplet) | `8` | 1/16. (Dotted) | `16` | 1T (1 Bar Triplet) |
| `1` | 1/64 | `9` | 1/8 | `17` | 1/2. (Half Dotted) |
| `2` | 1/32T | `10` | 1/4T (Quarter Triplet) | `18` | 1 Bar |
| `3` | 1/32 | `11` | 1/8. (Eighth Dotted) | `19` | 2T (2 Bars Triplet) |
| `4` | 1/16T | `12` | 1/4 | `20` | 1. (1 Bar Dotted) |
| `5` | 1/32. | `13` | 1/2T (Half Triplet) | `21` | 2 Bars |
| `6` | 1/16 | `14` | 1/4. (Quarter Dotted) | `22` | 4 Bars |
| `7` | 1/8T | `15` | 1/2 | | |

### B.2 Oscillator & Filter Enums
- **OSC Model (`SPTL + 00`)**: `0: PCM`, `1: VA`, `2: PCM-Sync`, `3: SuperSAW`, `4: Noise`
- **VA Waveform (`SPTL + 01`)**: `0: SAW`, `1: SQR`, `2: TRI`, `3: SIN`, `4: RAMP`, `5: JUNO`, `6: TRI2`, `7: TRI3`, `8: SIN2`
- **TVF Filter Type (`PTL + 31`)**: `0: OFF`, `1: LPF`, `2: BPF`, `3: HPF`, `4: PKG`, `5: LPF2`, `6: LPF3`
- **VCF Vintage Model (`SPTL + 12`)**: `0: FLAT`, `1: TYPE-JP`, `2: TYPE-M`, `3: TYPE-P`
- **LFO Waveform (`LFO + 00`)**: `0: SIN`, `1: TRI`, `2: SAW-UP`, `3: SAW-DW`, `4: SQR`, `5: RND`, `6: TRP`, `7: S&H`, `8: CHS`, `9: VSIN`, `10: STEP`
- **LFO Fade Mode (`LFO + 11`)**: `0: ON-IN`, `1: ON-OUT`, `2: OFF-IN`, `3: OFF-OUT`
- **Structure Type (`SPMT + 00/01`)**: `0: OFF`, `1: SYNC`, `2: RING`, `3: XMOD`, `4: XMOD2`
- **Output Assign (`PTL + 1A`)**: `0: DRY`, `1: MFX`
- **Drum Output Assign (`KPTL + 0E`)**: `0: DRY`, `1: MFX`, `2: COMP1`, `3: COMP2`, `4: COMP3`, `5: COMP4`, `6: COMP5`, `7: COMP6`

