# Ableton Push 1 Hardware Operation Bible: Definitive Reference Manual

The primary hardware operational specification, workflow guide, and technical reference for the **Ableton Push 1** (engineered in collaboration with Akai Professional, 2013). 

This document serves as the foundation for musicians, sound designers, and developers creating scripts, custom drivers, and standalone embedded integrations (such as [`pushy.py`](../scripts/pushy.py) and Zynthian UI `ctrldev` plugins).

> [!IMPORTANT]
> **Strict Hardware Scope — Push 1 Only:**
> This document pertains **exclusively** to the original **Ableton Push 1** hardware. It does not cover Push 2 (which introduced a color TFT display, revised buttons, and different pad mechanics) or Push 3 (which introduced MPE pads, a built-in audio interface, and standalone Linux processing). All physical layouts, display protocols, and operational workflows documented here are strictly specific to Push 1.

---

## 1. Hardware Architecture & Physical Specifications

Push 1 was co-developed by Ableton and Akai Professional to provide tactile, "eyes-off-the-computer" control over electronic music production, live performance, step sequencing, and synthesis.

```
+---------------------------------------------------------------------------------------------------+
|  [Tap] [Tempo] [Swing]        (1) (2) (3) (4)   (5) (6) (7) (8)     [Master Vol] [Ext 12V / USB]  |
|  [Metronome]             +-----------------------------------------+                              |
|                          | 4-Line x 68-Character Alphanumeric LCD  |   [Volume] [Pan/Send] [Track]|
|                          +-----------------------------------------+   [Clip]   [Device]   [Browse|
|                                                                                                   |
|  [Delete] [Undo]         [Upper Softkeys 1..8: Red/Amber/Yellow/Green] [Add Effect] [Add Track]   |
|  [Mute]   [Solo]                                                       [Note]       [Session]     |
|  [Stop]                  [Lower Softkeys 1..8: Full RGB Color Palette] [Select]     [Shift]       |
|                                                                                                   |
|  [Fixed Length]          +-----------------------------------------+   [1/32t] (Scene 1)          |
|  [Automation]            |                                         |   [1/32]  (Scene 2)          |
|  [Duplicate]             |                                         |   [1/16t] (Scene 3)          |
|  [New]                   |        8x8 RGB Silicone Pad Matrix       |   [1/16]  (Scene 4)          |
|                          |        (64 Velocity / Pressure Pads)    |   [1/8t]  (Scene 5)          |
|  [Record]                |                                         |   [1/8]   (Scene 6)          |
|  [Play]                  |                                         |   [1/4t]  (Scene 7)          |
|                          +-----------------------------------------+   [1/4]   (Scene 8)          |
|  [Touch Strip (24 LEDs)]                                                                          |
|  (Pitch Bend / Mod / Nav)                                              [Octave Up / Down]         |
|                                                                        [Scales] [User] [Repeat]   |
|                                                                        [Accent] [Cursor Keys Up/Dn|
+---------------------------------------------------------------------------------------------------+
```

### 1.1 Physical Dimensions & Chassis
- **Chassis Construction**: Heavy-duty structural aluminum top plate with an anodized black finish; scratch-resistant matte soft-touch perimeter bezel and rubberized non-slip base.
- **Width**: $370\text{ mm}$ ($14.57\text{ inches}$).
- **Depth**: $293\text{ mm}$ ($11.54\text{ inches}$).
- **Height**: $26\text{ mm}$ ($1.02\text{ inches}$) body chassis; $46\text{ mm}$ ($1.81\text{ inches}$) including top rotary encoders.
- **Weight**: $2.99\text{ kg}$ ($6.6\text{ lbs}$).
- **Security**: 1x standard Kensington Security Slot on the rear left edge.

### 1.2 Power Supply Architecture
Push 1 features a dual-mode power circuit:
1. **USB Bus Power ($5\text{V}, 500\text{ mA}$)**:
   - When connected solely via a USB 2.0/3.0 port, Push 1 is fully functional.
   - Internal power-saving logic automatically reduces LCD backlight brightness and dims all pad and button LEDs to roughly **$30\%$ of maximum luminosity**.
   - Suitable for portable studio use, mobile laptops, and low-light stage environments.
2. **External DC Power Supply ($12\text{V DC}, 1.25\text{A}$, Center-Positive)**:
   - Plugging in the external DC adapter activates the high-output LED drivers.
   - All 64 RGB pads, 24 touchstrip LEDs, and 71 button backlights illuminate at **$100\%$ full luminosity**, providing contrast for daylight stages and festival conditions.
   - Barrel jack dimensions: $5.5\text{ mm}$ outer diameter, $2.1\text{ mm}$ inner pin diameter.

> [!NOTE]
> Push 1 does **not** feature an onboard audio interface. Audio I/O, microphone inputs, and headphone amplification must be provided by external audio hardware (e.g., Blokas Pisound, USB audio interface, or host soundcard).

### 1.3 Rear Connectivity
- **1x USB 2.0 Type-B Port**: Connects to the host computer or embedded controller (e.g., Raspberry Pi 4 running Zynthian).
- **2x 1/4" ($6.35\text{ mm}$) TRS Footswitch Jacks**:
  - **Footswitch 1**: Configured by default as **Sustain Pedal** (`CC 64`). Supports continuous or momentary polarity switching.
  - **Footswitch 2**: Configured by default as **Transport / Clip Record Toggle** (`CC 69`). Stepping on the pedal punches into clip recording or toggles playback hands-free.
- **1x 12V DC Power Jack**: Center-positive barrel socket.

### 1.4 Dual USB MIDI Port Topology
Upon USB enumeration, Push 1 exposes two bidirectional MIDI endpoints to the operating system:
1. **Port 1 — `Ableton Push MIDI 1` ("Live Port")**:
   - The primary control surface interface.
   - Transmits encoder turns, pad strikes, button presses, touchstrip data, and aftertouch.
   - Receives SysEx commands for LCD line updates, pad RGB color assignments, and button LED states.
2. **Port 2 — `Ableton Push MIDI 2` ("User Port")**:
   - The secondary hardware interface, enabled when the **`[User]`** button (`CC 59`) is toggled.
   - Allows Push 1 to decouple individual controls or the entire pad matrix from the main host, routing raw MIDI data directly to external hardware synthesizers (e.g., Roland MC-101, modular MIDI interfaces, or Teensy voices) without host interference.

---

## 2. Interactive Surface & Physical Controls

Push 1 features a total of 64 expressive pads, 11 touch-sensitive continuous encoders, a 24-LED capacitive touchstrip, and 71 backlit rubber function buttons.

### 2.1 The 8x8 Silicone Pad Matrix (64 Pads)
- **Sensor Technology**: High-durability conductive silicone elastomer pads over high-density carbon interdigital contacts and force-sensing resistors.
- **Velocity Sensitivity**: Full 7-bit dynamic range ($1..127$). Dynamic curves (Linear, Logarithmic, Exponential) can be calibrated in hardware configuration.
- **Pressure Sensitivity (Aftertouch)**: Supports both **Channel Pressure (Monophonic Aftertouch)** and **Polyphonic Aftertouch** (scanned per-pad across the 8x8 grid).
- **RGB LED Backlighting**: Every pad contains a multi-chip RGB LED capable of rendering Ableton's 128-color indexed palette (ranging from dim track colors to vibrant playback indicators, flashing alerts, and record tallies).
- **Physical Layout & Indexing**:
  - Pads are addressed as an 8x8 matrix from **Bottom-Left (Row 0, Col 0 = MIDI Note 36 / C1)** to **Top-Right (Row 7, Col 7 = MIDI Note 99 / D#6)**.
  - Mathematical address formula: $\text{Note} = 36 + (\text{Row} \times 8) + \text{Col}$.

### 2.2 The 11 Touch-Sensitive Endless Rotary Encoders
Push 1 uses high-resolution continuous endless rotary encoders with integrated capacitive touch detection:
1. **8 Parameter Encoders (Above the LCD)**:
   - Dynamically mapped to whatever parameters are shown on the LCD columns below them (device parameters, mixer channels, track panning, clip settings).
   - **Capacitive Touch**: Touching the metal shaft of an encoder triggers an immediate touch event (`Note On 0..7`), enabling the LCD to display fine parameter names, engineering units, or temporarily un-hide automation values without needing to turn the knob!
   - **Relative Turn Output**: Turning the knob sends relative two's complement steps:
     - Clockwise turns transmit `CC` values $1..63$ (proportional to rotational speed).
     - Counter-clockwise turns transmit `CC` values $127..65$ (proportional to speed).
2. **1 Master Volume Encoder (Top Right)**:
   - Dedicated knob for Main Output volume. Touching it displays the Master Volume toast.
3. **1 Tempo Encoder (Top Left)**:
   - Controls session tempo in whole BPM steps. Holding **`[Shift]`** while turning adjusts tempo in fine **$0.1\text{ BPM}$ increments**.
4. **1 Swing Encoder (Top Left, Adjacent to Tempo)**:
   - Sets global groove and swing percentage ($0\%$ to $100\%$).

### 2.3 The Capacitive Touchstrip (Ribbon Controller)
- **Hardware**: $17\text{ cm}$ continuous capacitive touch ribbon situated vertically along the lower-left edge.
- **Optical Feedback**: 24 discrete white LEDs embedded beneath the ribbon surface reflect the current value or finger position.
- **Modes of Operation**:
  - **Pitch Bend Mode (Default)**: Center-sprung behavior. Placing a finger bends pitch up or down; releasing the finger snaps the LEDs and MIDI value back to center ($8192 / 0\text{ semitones}$).
  - **Modulation / Fader Mode**: Flat continuous controller. LEDs fill from bottom to top; releasing your finger leaves the value at its current level (sends `CC 1` or assigned target).
  - **Navigation / Bank Scrolling**: In Drum Rack mode, swiping the touchstrip scrolls up and down through the 128 pads in 16-pad drum banks. Holding `[Shift]` scrolls row-by-row (4 pads at a time).

### 2.4 Dedicated Hardware Pushbuttons & LED Topology
Push 1 features 71 backlit rubber pushbuttons grouped into distinct functional clusters:

| Cluster | Buttons | LED Type | Primary Purpose |
|---|---|---|---|
| **Upper Display Softkeys** | 8 Softkeys (Above LCD) | Bi-Color (Red/Amber/Green) | Device chain navigation, bank selection, view switching |
| **Lower Display Softkeys** | 8 Softkeys (Below LCD) | Full RGB (128 Colors) | Track selection, state toggle, parameter activation, page tabs |
| **Scene Launch Column** | 8 Buttons (`1/32t` to `1/4`) | Bi-Color (Amber/Green/Red) | Scene launching, step-sequencer resolution, repeat rates |
| **Transport Cluster** | `[Play]`, `[Record]` | Bi-Color (Green/Red) | Global transport start/stop and clip/session overdub record |
| **Workflow Modifiers** | `[Shift]`, `[Select]` | White Monochrome | Secondary shift shortcuts, selection without triggering |
| **Track State Controls** | `[Mute]`, `[Solo]`, `[Stop]` | Bi-Color (Amber/Yellow/Red)| Immediate track and clip muting, soloing, and stopping |
| **Grid Mode Toggles** | `[Note]`, `[Session]` | White Monochrome | Switches pad matrix between playing/sequencing and clip launching |
| **Editing Commands** | `[Undo]`, `[Delete]`, `[Duplicate]` | White Monochrome | Non-destructive editing, step clearing, object duplication |
| **Performance Tools** | `[Accent]`, `[Repeat]`, `[Fixed Length]` | White Monochrome | Full velocity lock, note repeat/arp, preset clip recording lengths |
| **Menu & System Modes** | `[Scales]`, `[User]`, `[Device]`, `[Browse]` | White Monochrome | Scale menus, hardware setup, device racks, and library browsing |
| **Navigation D-Pad** | `[▲]`, `[▼]`, `[◀]`, `[▶]` | White Monochrome | Bank switching, parameter pages, octave and cursor movement |

---

## 3. The Display Subsystem (4-Line x 68-Character LCD)

Push 1 features a custom **$4\text{ lines} \times 68\text{ characters}$ alphanumeric dot-matrix LCD** ($272$ characters total) illuminated by a high-contrast blue-white LED backlight.

```
+---------------------------------------------------------------------------------------------------+
| Param 1   Param 2   Param 3   Param 4   Param 5   Param 6   Param 7   Param 8                     | (Line 0)
| Cutoff    Reson     FilterEnv FilterDec Attack    Decay     Sustain   Release                     | (Line 1)
| 1.25 kHz  45.0 %    +32.0 %   250 ms    12.0 ms   450 ms    0.0 dB    1.20 s                      | (Line 2)
| [||||   ] [|||    ] [|||||  ] [||     ] [|      ] [||||   ] [|||||| ] [|||    ]                   | (Line 3)
+---------------------------------------------------------------------------------------------------+
    Col 1     Col 2     Col 3     Col 4     Col 5     Col 6     Col 7     Col 8
```

### 3.1 Column Formatting Modes
The 68-character width is divided into either an **8-Column** or a **4-Column** layout:
1. **8-Column Mode (Standard Parameter & Mixer View)**:
   - Used for the 8 rotary encoders directly above the display.
   - Each column is exactly **8 characters wide**, separated by a 1-character whitespace ($8 \times 8 = 64$ characters, plus 4 spacer characters across the screen = 68 characters).
   - Line 0: Category / Device / Parameter Name (e.g., `Cutoff  `).
   - Line 1: Sub-category or Secondary Parameter (e.g., `Reson   `).
   - Line 2: Numeric Value with Engineering Units (e.g., `1.25 kHz`, `-6.0 dB`, `75.0 %`).
   - Line 3: Custom graphical bar graph or pan position glyphs.
2. **4-Column Mode (Preset Browser & Wide Information View)**:
   - Used when browsing device libraries, audio clips, and samples.
   - Each column is **17 characters wide** ($4 \times 17 = 68$ characters).
   - Displays hierarchical folder trees, long preset names, and device chains without truncation.

### 3.2 Custom Glyphs & Graphical Characters
The LCD controller possesses internal Character Generator RAM (CGRAM) allowing custom $5\times 8$ pixel glyphs at ASCII indices `0x00`–`0x1F`:
- **Horizontal Bar Graphs (`render_bar`)**: 8 progressive horizontal fill levels used to render parameter levels, mixer volumes, and send amounts.
- **Center-Zero Pan Meters (`render_pan`)**: Bi-directional meter glyphs showing Left/Right pan positions with a distinct center tick.
- **Folder & File Indicators**: Arrows (`▶`, `▼`), folder icons, and checkmarks for menu navigation and hot-swapping.

### 3.3 Transient Overlay Banners ("Toasts")
When a global control is touched or turned, the bottom lines of the LCD temporarily suspend their normal channel/parameter data to display a prominent popup banner:
- **Master Volume**: Touching the Master encoder displays a full-width Master Volume dB bar and numerical readout.
- **Tempo Banner**: Turning the Tempo encoder displays the current BPM to two decimal places (e.g., `TEMPO: 124.00 BPM`) and metronome status.
- **Swing Banner**: Displays the current groove template and swing amount (e.g., `SWING: 56%`).
- Releasing the control clears the toast after a $750\text{ ms}$ timeout, cleanly restoring previous parameter names.

---

## 4. Comprehensive Operational Modes & Workflows

### 4.1 Session Mode (Clip & Scene Launching)
Pressing the **`[Session]`** button (`CC 51`) switches the 8x8 pad matrix into an 8-track, 8-scene clip launcher mirroring the host Session View.

```
       Track 1    Track 2    Track 3    Track 4    Track 5    Track 6    Track 7    Track 8
     +----------+----------+----------+----------+----------+----------+----------+----------+
Sc 1 |  Clip 1  |  Clip 1  |  [Play]  |  Empty   |  Clip 1  |  Clip 1  |  [Rec]   |  Clip 1  | -> [1/32t] (Launch Scene 1)
Sc 2 |  Clip 2  |  Clip 2  |  Clip 2  |  Clip 2  |  Empty   |  Clip 2  |  Clip 2  |  Empty   | -> [1/32]  (Launch Scene 2)
Sc 3 |  [Stop]  |  Empty   |  Clip 3  |  Clip 3  |  Clip 3  |  Empty   |  Clip 3  |  Clip 3  | -> [1/16t] (Launch Scene 3)
Sc 4 |  Clip 4  |  Clip 4  |  Clip 4  |  Empty   |  Clip 4  |  Clip 4  |  Clip 4  |  Clip 4  | -> [1/16]  (Launch Scene 4)
Sc 5 |  Clip 5  |  Clip 5  |  Empty   |  Clip 5  |  Clip 5  |  Clip 5  |  Empty   |  Clip 5  | -> [1/8t]  (Launch Scene 5)
Sc 6 |  Clip 6  |  Clip 6  |  Clip 6  |  Clip 6  |  Empty   |  Clip 6  |  Clip 6  |  Clip 6  | -> [1/8]   (Launch Scene 6)
Sc 7 |  Empty   |  Empty   |  Clip 7  |  Clip 7  |  Clip 7  |  Empty   |  Clip 7  |  Empty   | -> [1/4t]  (Launch Scene 7)
Sc 8 |  Clip 8  |  Clip 8  |  Clip 8  |  Empty   |  Clip 8  |  Clip 8  |  Clip 8  |  Clip 8  | -> [1/4]   (Launch Scene 8)
     +----------+----------+----------+----------+----------+----------+----------+----------+
       [Trk 1]    [Trk 2]    [Trk 3]    [Trk 4]    [Trk 5]    [Trk 6]    [Trk 7]    [Trk 8]
```

#### Pad Color Feedback in Session Mode
- **Unlit (Off)**: No clip exists in this slot.
- **Solid Color (Track Hue)**: Clip exists and is stopped/idle.
- **Flashing Green**: Clip is queued to play on the next quantization boundary.
- **Pulsing Green**: Clip is currently playing.
- **Flashing Red**: Clip is queued to record.
- **Pulsing Red**: Clip is actively recording audio or MIDI.
- **Dim Amber**: Clip contains audio/MIDI data but its track is muted.

#### Scene Launching
The 8 buttons along the right side of the pad grid (`CC 36..43`, labelled `1/4` through `1/32t`) function as **Scene Launch Buttons**:
- Pressing a Scene button launches all clips in that horizontal row simultaneously.
- Scene buttons pulse green when their respective scene is actively playing.

#### Navigation & Session Overview
- **D-Pad Cursor Keys (`[▲]`, `[▼]`, `[◀]`, `[▶]`)**: Shifts the 8x8 "Session Ring" across your project by one track or one scene.
- **Session Overview (Zoom)**: Hold down **`[Shift]`** while in Session Mode. The 64 pads zoom out so that each pad represents an entire $8\times 8$ block of clips:
  - Tapping a pad instantly relocates the Session Ring to that section of the project.

---

### 4.2 Note Mode — Drum Racks (The 3-Zone Beat Factory)
When an active MIDI track contains a Drum Rack, pressing **`[Note]`** (`CC 50`) divides the 64 pads into three functional zones:

```
+---------------------------------------------------------------------------------------------------+
|  [Step 1]  [Step 2]  [Step 3]  [Step 4]  [Step 5]  [Step 6]  [Step 7]  [Step 8]  (Row 7)          |
|  [Step 9]  [Step 10] [Step 11] [Step 12] [Step 13] [Step 14] [Step 15] [Step 16] (Row 6)          |
|  [Step 17] [Step 18] [Step 19] [Step 20] [Step 21] [Step 22] [Step 23] [Step 24] (Row 5)  TOP 32  |
|  [Step 25] [Step 26] [Step 27] [Step 28] [Step 29] [Step 30] [Step 31] [Step 32] (Row 4)  PADS    |
|  ======================================================================================           |
|  [Pad 13]  [Pad 14]  [Pad 15]  [Pad 16]  |  [Page 13] [Page 14] [Page 15] [Page 16] (Row 3)       |
|  [Pad 9]   [Pad 10]  [Pad 11]  [Pad 12]  |  [Page 9]  [Page 10] [Page 11] [Page 12] (Row 2)       |
|  [Pad 5]   [Pad 6]   [Pad 7]   [Pad 8]   |  [Page 5]  [Page 6]  [Page 7]  [Page 8]  (Row 1)       |
|  [Pad 1]   [Pad 2]   [Pad 3]   [Pad 4]   |  [Page 1]  [Page 2]  [Page 3]  [Page 4]  (Row 0)       |
|       LOWER-LEFT: 16 DRUM PADS           |       LOWER-RIGHT: 16 LOOP LENGTH PAGES                |
+---------------------------------------------------------------------------------------------------+
```

#### Zone 1: Lower-Left 4x4 (16 Drum Pads)
- Triggers 16 individual drum sounds (e.g., Kick, Snare, Claps, Hats).
- Hitting a pad plays the sound live, illuminates it in bright yellow, and selects it for step-sequencing above.
- **Pad Colors**:
  - Yellow: Standard drum voice.
  - Light Blue: Selected drum voice currently displayed on the step sequencer.
  - Cyan: Drum pads assigned to the same choke group.
  - Green (flashing): Sound is actively sounding.

#### Zone 2: Lower-Right 4x4 (16 Loop Length Pages)
- Represents the loop length and playback position of the current clip.
- Each pad represents a measure (or pattern page depending on grid resolution).
- **Selecting Loop Length**:
  - Tapping a single pad restricts the loop to that measure.
  - Touching and holding the first pad while tapping a second pad sets an arbitrary multi-measure loop bracket (e.g., bars 1 through 4).
- The actively playing bar pulses in green; bars included in the loop remain solid white; bars outside the loop remain dim.

#### Zone 3: Upper 4x8 (32 Sequencer Steps)
- Displays step triggers for the drum sound selected in Zone 1.
- Pads illuminate solid yellow/amber for active steps.
- A **moving green light** traverses the step grid representing the current playhead position.
- Tapping an empty pad creates a note; tapping an active pad removes it.
- **Step Parameter Editing**: Pressing and holding an active step displays that note's **Nudge (micro-timing)**, **Length**, and **Velocity** on the LCD, allowing precise adjustment using the rotary encoders above!

#### Drum Rack Bank Navigation & The Touchstrip
Drum Racks can hold up to 128 individual sounds across 8 banks of 16.
- **Touchstrip Scrolling**: Swiping a finger along the capacitive touchstrip scrolls up and down through the 128 sounds in 16-pad increments.
- **Row-by-Row Fine Scrolling**: Hold **`[Shift]`** while sliding the touchstrip (or press `[Octave Up]` / `[Octave Down]`) to shift the lower-left 4x4 pad grid by **single rows (4 pads)** at a time!

#### 16-Velocities Mode
If you prefer expressive finger drumming with predictable dynamics:
- Hold **`[Select]`** and press the active drum pad. 
- You can map the 16 drum pads to play the **same single drum sound across 16 stepped velocity levels** (from soft ghost notes to maximum $127$ accents).

---

### 4.3 Note Mode — Melodic Instruments (Isomorphic 64-Pad Grid)
When an active MIDI track contains a melodic synthesizer, sampler, or Simpler instrument, pressing **`[Note]`** turns the entire 8x8 matrix into a continuous **isomorphic keyboard**:

```
Row 7: [ F3] [ F#3] [ G3] [ G#3] [ A3] [ A#3] [ B3] [ C4] -> Note 92..99
Row 6: [ C3] [ C#3] [ D3] [ D#3] [ E3] [ F3] [ F#3] [ G3] -> Note 84..91
Row 5: [ G2] [ G#2] [ A2] [ A#2] [ B2] [ C3] [ C#3] [ D3] -> Note 76..83
Row 4: [ D2] [ D#2] [ E2] [ F2] [ F#2] [ G2] [ G#2] [ A2] -> Note 68..75
Row 3: [ A1] [ A#1] [ B1] [ C2] [ C#2] [ D2] [ D#2] [ E2] -> Note 60..67
Row 2: [ E1] [ F1]  [ F#1] [ G1] [ G#1] [ A1] [ A#1] [ B1] -> Note 52..59
Row 1: [ B0] [ C1]  [ C#1] [ D1] [ D#1] [ E1] [ F1]  [ F#1] -> Note 44..51
Row 0: [ F#0] [ G0] [ G#0] [ A0] [ A#0] [ B0] [ C1]  [ C#1] -> Note 36..43
       Col 0  Col 1  Col 2  Col 3  Col 4  Col 5  Col 6  Col 7
```

#### Isomorphic Interval Logic (4ths Tuning)
By default, the pads are arranged in **Fourths** (like the lowest four strings of a standard bass guitar, or Chapman Stick tuning):
- Moving **1 pad to the right** increases pitch by **1 semitone** (or 1 scale degree in In-Key mode).
- Moving **1 pad directly up** increases pitch by exactly **5 semitones (a perfect 4th)**.
- **Symmetric Chord Shapes**: Because interval relationships remain mathematically identical everywhere on the grid, any chord shape (Major 7th, Minor 9th, Sus4) uses the **exact same finger fingering pattern regardless of the root key**!

#### Scale Selection & The `[Scales]` Menu
Pressing the **`[Scales]`** button (`CC 58`) opens the musical scale configuration screen on the 4x68 LCD:

```
+---------------------------------------------------------------------------------------------------+
| Scale Type: Minor             Root Key: D                     Mode: In Key      Interval: 4ths    |
| [Major   ] [Minor   ] [Dorian  ] [Phrygian] [Lydian  ] [Mixolyd] [Locrian ] [Pentaton]            |
| [C       ] [C#      ] [D       ] [D#      ] [E       ] [F       ] [F#      ] [G       ]            |
| In Key: [ON ]          Chromatic: [OFF]     Interval: [4ths]    Fixed: [OFF]                      |
+---------------------------------------------------------------------------------------------------+
```

- **Root Key**: Choose from all 12 chromatic pitches ($C, C\sharp, D, D\sharp, E, F, F\sharp, G, G\sharp, A, A\sharp, B$).
- **Scale Types (Over 30 Supported)**: Major, Minor, Dorian, Phrygian, Lydian, Mixolydian, Locrian, Minor Pentatonic, Major Pentatonic, Blues, Harmonic Minor, Melodic Minor, Whole Tone, Diminished, Hungarian Minor, Arabian, etc.
- **In-Key vs. Chromatic Mode**:
  - **In-Key Mode (`In Key: ON`)**: Only notes belonging to the selected scale are mapped to the 64 pads. Out-of-scale notes are removed completely. It is **impossible to hit a wrong note**, making it ideal for fast, improvisational live soloing!
  - **Chromatic Mode (`Chromatic: ON`)**: All 12 semitones remain physically present on the grid. Pads in the scale illuminate white; the root notes illuminate blue/orange; out-of-scale notes remain unlit.
- **Fixed Mode**:
  - When `Fixed: OFF` (default), the lowest pad (Row 0, Col 0) reflects the current scale transposition.
  - When `Fixed: ON`, the note $C$ is locked permanently to Row 0, Col 0 regardless of key changes.

#### Octave Shifting & Ribbon Pitch Bend
- **`[Octave Up]` (`CC 55`) & `[Octave Down]` (`CC 54`)**: Transposes the entire 64-pad grid up or down across an 8-octave range ($C-2$ to $C8$). The LCD briefly displays the new range (e.g., `OCTAVE: C2 - G6`).
- **Touchstrip Ribbon**: Provides spring-loaded pitch bending up and down, or smooth modulation wheel sweeps when toggled with `[Shift]`.

---

### 4.4 Melodic Step Sequencing (Live 9.1+)
Introduced in Ableton Live 9.1, Melodic Step Sequencing transforms Push 1 into a classic polyphonic step sequencer:

```
+---------------------------------------------------------------------------------------------------+
|  [P1]    [P2]    [P3]    [P4]    [P5]    [P6]    [P7]    [P8]   (Loop Page & Playhead Timeline)   |
|  -----------------------------------------------------------------------------------------------  |
|  [Step 1][Step 2][Step 3][Step 4][Step 5][Step 6][Step 7][Step 8] (High Pitch Degree / G4)        |
|  [Step 1][Step 2][Step 3][Step 4][Step 5][Step 6][Step 7][Step 8] (Pitch Degree / E4)             |
|  [Step 1][Step 2][Step 3][Step 4][Step 5][Step 6][Step 7][Step 8] (Pitch Degree / D4)             |
|  [Step 1][Step 2][Step 3][Step 4][Step 5][Step 6][Step 7][Step 8] (Pitch Degree / C4 - Root)      |
|  [Step 1][Step 2][Step 3][Step 4][Step 5][Step 6][Step 7][Step 8] (Pitch Degree / B3)             |
|  [Step 1][Step 2][Step 3][Step 4][Step 5][Step 6][Step 7][Step 8] (Pitch Degree / A3)             |
|  [Step 1][Step 2][Step 3][Step 4][Step 5][Step 6][Step 7][Step 8] (Lowest Pitch Degree / G3)      |
+---------------------------------------------------------------------------------------------------+
```

#### How to Engage Melodic Step Sequencing
1. Select an instrument track.
2. Press **`[Note]`** once to access the live isomorphic keyboard.
3. Press **`[Note]` a second time** to toggle into **Melodic Step Sequencer Mode**.

#### Layout Architecture
- **Vertical Axis (Rows 0..6)**: Represents pitches in your selected scale (ascending from bottom to top). Root notes are illuminated in blue.
- **Horizontal Axis (Columns 0..7)**: Represents 8 consecutive time divisions (steps) at the current grid resolution (e.g., 16th notes).
- **Top Row (Row 7)**: Acts as the **Loop Page Bar**:
  - Displays which 8-step measure is currently being edited.
  - A flashing green cursor indicates the active playback position.
  - Tapping a pad in Row 7 instantly jumps the edit view to that measure.
  - Double-tapping a pad loops playback strictly to that measure.
- **Pitch Navigation**:
  - Sliding your finger on the **Touchstrip** scrolls the pitch window up and down across octaves.
  - `[Octave Up]` and `[Octave Down]` shift the melodic view by full octaves.

#### Polyphonic Step Programming
- Tap any pad to insert a note at that specific pitch and step.
- Tap multiple pads in the same column to program **polyphonic chords** on that step.
- **Per-Step Parameter Editing**: Hold down any active note pad. The top LCD encoders reveal:
  - **Nudge**: Shifts note start time earlier or later in sub-tick increments.
  - **Length**: Extends note duration across multiple steps (the pads illuminate across the sequence to show sustained duration).
  - **Velocity**: Adjusts per-note velocity level ($1..127$).
  - **Fine Pitch**: Fine-tunes note frequency in cents.

---

### 4.5 Mixer & Track Control Modes
Push 1 provides dedicated hardware mixing modes accessed via the mode buttons to the right of the LCD:

```
+---------------------------------------------------------------------------------------------------+
| Track 1   Track 2   Track 3   Track 4   Track 5   Track 6   Track 7   Track 8                     |
| Audio 1   Drums     Bassline  Lead      Vocal     Reverb    Delay     Master                      |
| -2.5 dB   -0.0 dB   -6.0 dB   -12.0 dB  -3.5 dB   -inf dB   -inf dB   -0.2 dB                     |
| [|||||  ] [|||||| ] [||||   ] [|||    ] [|||||  ] [       ] [       ] [|||||| ]                   |
+---------------------------------------------------------------------------------------------------+
   (Enc 1)   (Enc 2)   (Enc 3)   (Enc 4)   (Enc 5)   (Enc 6)   (Enc 7)   (Enc 8)
```

1. **`[Volume]` Mode (`CC 114`)**:
   - The 8 parameter encoders control volume faders for the 8 visible tracks.
   - The LCD displays exact decibel levels (`-inf` to `+6.0 dB`) and graphical bar meters.
2. **`[Pan & Send]` Mode (`CC 115`)**:
   - Successive presses cycle between **Pan**, **Send A**, **Send B**, **Send C**, etc.
   - Panning shows center-zero bi-directional bar graphs (`<C>`, `15L`, `32R`).
   - Sends display exact send level in dB.
3. **`[Track]` Mode (`CC 112` — Single Channel Strip View)**:
   - Encoders 1..8 control the full channel strip of the **single active track**:
     - Encoder 1: Track Volume.
     - Encoder 2: Track Panning.
     - Encoders 3..8: Sends A through F.
4. **`[Master]` Button (`CC 28`)**:
   - Instantly focuses the mixer on the Master Output bus and master effect rack.

---

### 4.6 Device & Parameter Editing Mode
Pressing **`[Device]`** (`CC 110`) maps Push 1's 8 encoders to the parameters of the active instrument, VST plugin, or audio effect:

```
+---------------------------------------------------------------------------------------------------+
| [Analog]  [Filter]  [AmpEnv]  [LFO 1]   [Chorus]  [Reverb]  [Delay]   [Limiter]  (Upper Softkeys) |
| Freq      Resonance EnvAmt    Decay     LFO Rate  Depth     Wet/Dry   Output                      |
| 440 Hz    0.72      +45 %     650 ms    2.50 Hz   50.0 %    30.0 %    -0.5 dB                     |
| [||||   ] [|||||  ] [||||   ] [|||||  ] [|||    ] [||||   ] [|||    ] [|||||| ]                   |
+---------------------------------------------------------------------------------------------------+
```

- **Device Chain Navigation**:
  - The **Upper Softkeys** display each device in the track's signal chain.
  - Tapping an upper softkey focuses that device on the LCD.
- **8-Parameter Banking**:
  - Complex devices with dozens of controls are organized into banks of 8 parameters.
  - Use the **`[◀]` and `[▶]` D-pad buttons** to cycle through parameter pages (e.g., `Oscillator 1`, `Filter`, `Envelopes`, `Mod Matrix`).
- **Capacitive Parameter Interrogation**:
  - Lightly resting a finger on any encoder displays that parameter's full un-truncated name and current value without altering its state.
- **Fine Adjustment**:
  - Turning an encoder while holding **`[Shift]`** enables high-resolution adjustments (e.g., fractional Hertz or $0.1\text{ dB}$ steps).

---

### 4.7 Browser & Preset Selection Mode
Pressing **`[Browse]`** (`CC 111`) opens the file and preset library on the 4x68 LCD in **4-Column Mode**:

```
+---------------------------------------------------------------------------------------------------+
| Instruments      | Operator         | Bass             | Sub Bass 01.adv                         |
| Drum Racks       | Analog           | Lead             | Acid Square.adv                         |
| Audio Effects    | Electric         | Pad              | Deep Mellow.adv                         |
| MIDI Effects     | Tension          | Strings          | FM Growl.adv                            |
+---------------------------------------------------------------------------------------------------+
     Col 1              Col 2              Col 3              Col 4
```

- **Column 1**: Top-level category (Instruments, Drums, Effects, User Library).
- **Column 2**: Device or engine type.
- **Column 3**: Preset subfolder / category.
- **Column 4**: Individual sound preset files.
- **Navigation**:
  - Turning Encoders 1..4 scrolls through the list in the respective column.
  - Pressing the **Lower Softkeys** confirms selections, drills into subfolders, or loads the selected preset.
  - Pressing **`[Browse]`** again closes the browser and returns to the previous performance mode.

---

## 5. Performance Expressiveness & Workflow Modifiers

### 5.1 Real-Time Performance Modifiers
- **`[Accent]` (`CC 57`)**:
  - When engaged (button illuminated), all pad hits are forced to maximum MIDI velocity (**$127$**), bypassing velocity dynamics. Ideal for driving vintage analog synth patches or programming consistent techno hi-hats.
- **`[Repeat]` (`CC 56` — Note Repeat / Arpeggiator)**:
  - When held or latched, holding down any pad generates continuous repeated notes synchronized to the master clock.
  - The 8 right-hand Scene buttons (`CC 36..43`) select note repeat divisions:
    - `1/4`: Quarter notes
    - `1/4t`: Quarter note triplets
    - `1/8`: Eighth notes
    - `1/8t`: Eighth note triplets
    - `1/16`: Sixteenth notes (standard)
    - `1/16t`: Sixteenth note triplets
    - `1/32`: Thirty-second notes
    - `1/32t`: Thirty-second note triplets
  - **Pressure Modulates Volume**: Pressing harder on the pad increases note repeat volume in real time via continuous aftertouch pressure!
- **`[Fixed Length]` (`CC 90`)**:
  - Pressing `[Fixed Length]` toggles preset recording durations.
  - Pressing and holding `[Fixed Length]` displays length choices on the lower softkeys: **1 Bar, 2 Bars, 4 Bars, 8 Bars, 16 Bars**.
  - When activated, pressing `[Record]` automatically ends recording and switches into seamless playback loop mode the moment the chosen duration elapses!
- **`[Double]` (`CC 117`)**:
  - Instantly doubles the length of the currently playing clip (e.g., turns a 2-bar loop into a 4-bar loop) and duplicates all existing MIDI notes into the second half for immediate variation development.
- **`[Quantize]` (`CC 116`)**:
  - Pressing `[Quantize]` snaps all notes in the active clip to the current grid division.
  - Holding `[Quantize]` opens the quantization preferences menu on the LCD:
    - **Quantize Amount**: $0\%$ to $100\%$ (allows non-destructive loose human groove timing).
    - **Grid Division**: 1/4 to 1/32t.
    - **Swing**: Applies groove template offsets.
- **`[Automation]` (`CC 89`)**:
  - Toggles motion recording. When engaged (LED red), turning any encoder during playback writes continuous parameter automation curves directly into the active clip.
- **`[Duplicate]` (`CC 88`)**:
  - Duplicates the selected clip, scene, or drum pad into the next available slot.
- **`[New]` (`CC 87`)**:
  - Prepares the next empty clip slot on the armed track and initiates recording immediately without requiring manual Session navigation.

---

## 6. Lesser-Known Shortcuts, Hidden Tricks & Deep Workflow Secrets

The following operational shortcuts and hidden functions were documented across production studios and power-user discovery (including Ableton 9.1.4+ releases and the Carillon Audio research):

### 6.1 Drum Rack Deep Manipulation Shortcuts
- **Batch Edit All Notes for a Specific Drum**:
  - In Drum Step Sequencer mode, hold **`[Select]`** and press a drum pad.
  - The LCD top encoders now adjust **Nudge, Length, Fine, and Velocity for EVERY note programmed for that drum across the entire clip simultaneously**!
- **Selective Quantization per Drum Sound**:
  - Instead of quantizing the entire drum beat, hold **`[Quantize]`** and press a single drum pad. Only notes belonging to that specific drum (e.g., Snare) are quantized; your loose human hi-hats remain completely untouched!
- **Selective Note Deletion per Drum Sound**:
  - Hold **`[Delete]`** and press a drum pad. Only the notes belonging to that specific drum are wiped from the pattern.
- **Muting & Soloing Individual Drum Voices**:
  - Hold **`[Mute]`** and tap a drum pad to instantly mute that sound.
  - Hold **`[Solo]`** and tap a drum pad to solo that sound.
  - Hold **`[Mute]`** and tap an active step pad in the top sequencer grid to **mute just that individual step trigger** without deleting it!
- **Fast 1-Row Drum Scrolling**:
  - Hold **`[Shift]`** while sliding your finger on the touchstrip to scroll the drum rack by **single rows (4 pads)** instead of jumping full 16-pad banks.

### 6.2 Session & Navigation Shortcuts
- **Stopping Clips from Note Mode**:
  - You do **not** need to leave Note Mode to stop an active clip!
  - Hold the **`[Stop]`** button (below Master) and press the **Lower Softkey** corresponding to that track under the LCD screen. The clip on that track stops instantly.
- **Muting & Soloing Tracks from Note Mode**:
  - Hold **`[Mute]`** or **`[Solo]`** and press any track's **Lower Softkey** under the LCD screen to toggle track states without leaving Note or Device mode.
- **Redo Shortcut**:
  - Press **`[Shift] + [Undo]`** to Redo the last undone action.
- **Quick Track / Device Deletion**:
  - While in `[Track]` or `[Device]` display mode, hold **`[Delete]`** and press the corresponding upper or lower softkey to instantly remove that track or effect without touching the mouse.
- **Group Track Expansion**:
  - Press and hold a Group Track's selection softkey to expand or collapse all child tracks within the group on Push's screen.
- **Momentary vs. Latching Modifiers**:
  - Tapping `[Mute]`, `[Solo]`, or `[Select]` latches the mode on.
  - Holding `[Mute]` or `[Solo]` for more than $300\text{ ms}$ acts as a **momentary modifier**: release the button and Push instantly reverts to its previous operational mode!

---

## 7. Global Hardware Configuration & Pad Calibration Menu

Push 1 features a hidden hardware calibration and configuration menu accessed directly on the device:

### 7.1 Accessing the Hardware Setup Menu
- Press and hold the **`[User]`** button (`CC 59`) for two seconds while connected to the host.
- The 4x68 LCD switches to the **Hardware Calibration Screen**:

```
+---------------------------------------------------------------------------------------------------+
| Pad Threshold: 20             Velocity Curve: Linear          Aftertouch Threshold: 35            |
| Threshold: [20 ]              Curve: [Linear     ]            Aftertouch: [35 ]                   |
| Dynamic Range: [85 ]          Ribbon Mode: [PitchBend]        LED Brightness: [100%]              |
| Push 1 Firmware: v1.12        Serial: AKAI-PUSH-1-PRO         Power: 12V DC Adapter Connected     |
+---------------------------------------------------------------------------------------------------+
   (Enc 1: Thresh) (Enc 2: Curve)  (Enc 3: Dyn)   (Enc 4: AT)     (Enc 5: Ribbon) (Enc 6: Bright)
```

### 7.2 Calibration Parameters
1. **Pad Threshold (`Pad Threshold`, $0..127$)**:
   - Sets the minimum force required to register a pad strike.
   - Low values ($5..15$) allow feather-light finger taps and delicate ghost notes, but can risk accidental triggering or vibration crosstalk in loud bass-heavy environments.
   - Higher values ($25..40$) require deliberate strikes, ideal for aggressive drumming styles.
2. **Velocity Curve (`Velocity Curve`)**:
   - Selects the mathematical velocity mapping:
     - `Linear`: $1:1$ proportional velocity scaling.
     - `Logarithmic 1..3`: Maximizes volume on medium strikes; ideal for synth leads.
     - `Exponential 1..3`: Requires very hard strikes to reach $127$; ideal for acoustic drum dynamics.
3. **Dynamics / Gain (`Dynamic Range`)**:
   - Scales the span between the softest registered note and maximum velocity.
4. **Aftertouch Threshold (`Aftertouch Threshold`)**:
   - Sets the pressure barrier required before Channel Pressure / Poly Aftertouch data begins streaming.
5. **Touchstrip Mode (`Ribbon Mode`)**:
   - Toggles whether the ribbon operates as center-sprung `PitchBend` or flat `ModWheel` / `Continuous CC`.

---

## 8. Hardware Limitations, Boundaries & Design Gotchas

When engineering drivers, standalone bridges, or firmware for Push 1, the following physical and architectural limitations must be respected:

1. **Alphanumeric Character Display Only (No Bitmaps)**:
   - Push 1 has a character-based dot-matrix LCD ($4\times 68$ chars), **not** a graphical pixel display like Push 2 or Push 3.
   - You cannot render arbitrary waveforms, spectrum analyzers, or high-resolution graphic curves. Custom graphics are strictly limited to the 32 custom CGRAM $5\times 8$ glyphs (indices `0x00`–`0x1F`).
2. **USB MIDI Buffer Flooding & Dirty-Line Diffing**:
   - Transmitting a full 4-line display refresh requires 4 separate SysEx packets totaling $308\text{ bytes}$.
   - Flooding the display with redundant updates at $60\text{ Hz}$ saturates the standard USB MIDI endpoint, resulting in perceptible pad latency and dropped encoder ticks!
   - **Requirement**: Always implement **dirty-line diffing** (as demonstrated in [`scripts/pushy.py`](../scripts/pushy.py)). Compare current text lines against a shadow buffer and transmit SysEx lines **only when character contents actually change**.
3. **USB Bus Power Dimming**:
   - Relying solely on $5\text{V}$ USB bus power restricts LED backlights to $\sim 30\%$ luminosity. In brightly lit studios or daylight performances, always connect the external $12\text{V DC}$ power supply.
4. **Encoder Relative Turn Acceleration**:
   - The endless rotary encoders output relative two's complement step ticks ($1..63$ forward, $127..65$ backward).
   - Acceleration and non-linear velocity ballistics must be implemented in host software. Slow turns increment values by $1$; rapid turns must scale exponentially to navigate broad parameter spans.
5. **Polyphonic Aftertouch Processing Load**:
   - While Push 1's hardware matrix scans polyphonic pressure across all 64 pads, transmitting 64 continuous streams of poly aftertouch can overwhelm older MIDI hardware and low-power microcontrollers. Host software should filter or convert poly aftertouch to channel pressure when driving external synthesizers (e.g., Roland MC-101).

---

## 9. Comprehensive Hardware CC & Note Reference Table

For rapid reference during development, the complete physical mapping of Ableton Push 1 is summarized below:

### 9.1 Continuous Controllers (Knobs, Touchstrip & Modifiers)

| Physical Control | Type | MIDI Channel | Hex / Dec Identifier | Value Range / Behavior |
|---|---|---|---|---|
| **Tempo Encoder** | Endless Rotary | Ch 1 | `CC 14` (`0x0E`) | Rel 2's Comp ($1..63$ CW, $127..65$ CCW) |
| **Swing Encoder** | Endless Rotary | Ch 1 | `CC 15` (`0x0F`) | Rel 2's Comp ($1..63$ CW, $127..65$ CCW) |
| **Track Encoders 1..8** | Endless Rotary | Ch 1 | `CC 71..78` (`0x47..0x4E`) | Rel 2's Comp ($1..63$ CW, $127..65$ CCW) |
| **Master Encoder** | Endless Rotary | Ch 1 | `CC 79` (`0x4F`) | Rel 2's Comp ($1..63$ CW, $127..65$ CCW) |
| **Encoder Touch 1..8** | Capacitive Touch| Ch 1 | `Notes 0..7` (`0x00..0x07`)| Velocity $127$ (Touch), $0$ (Release) |
| **Master Touch** | Capacitive Touch| Ch 1 | `Note 8` (`0x08`) | Velocity $127$ (Touch), $0$ (Release) |
| **Swing Touch** | Capacitive Touch| Ch 1 | `Note 9` (`0x09`) | Velocity $127$ (Touch), $0$ (Release) |
| **Tempo Touch** | Capacitive Touch| Ch 1 | `Note 10` (`0x0A`)| Velocity $127$ (Touch), $0$ (Release) |
| **Touchstrip (Ribbon)** | Capacitive Ribbon| Ch 1 | Pitch Bend / `CC 1` | 14-bit Pitch Bend ($0..16383$) or $0..127$ |
| **Footswitch 1** | 1/4" Jack | Ch 1 | `CC 64` (`0x40`) | Sustain ($0$ or $127$) |
| **Footswitch 2** | 1/4" Jack | Ch 1 | `CC 69` (`0x45`) | Toggle Transport / Record ($0$ or $127$) |

### 9.2 Pad Matrix (64 Pads)

| Coordinates | Physical Location | MIDI Note | Octave (In-Key Standard) |
|---|---|---|---|
| Row 0, Col 0 | Bottom-Left Pad | `Note 36` (`0x24`) | C1 |
| Row 0, Col 7 | Bottom-Right Pad | `Note 43` (`0x2B`) | G1 |
| Row 7, Col 0 | Top-Left Pad | `Note 92` (`0x5C`) | G#5 |
| Row 7, Col 7 | Top-Right Pad | `Note 99` (`0x63`) | D#6 |

### 9.3 Display Softkeys & Scene Buttons

| Button Group | Physical Label | CC Range (Dec / Hex) | LED Color Support |
|---|---|---|---|
| **Upper Softkeys 1..8** | Display Tops 1..8 | `CC 20..27` (`0x14..0x1B`) | Bi-Color (Off, Red, Amber, Yellow, Green) |
| **Lower Softkeys 1..8** | Display Bottoms 1..8 | `CC 102..109` (`0x66..0x6D`) | Full RGB Palette (128 Indexed Colors) |
| **Scene Buttons 1..8** | `1/32t` through `1/4` | `CC 43..36` (`0x2B..0x24`) | Bi-Color (Off, Red, Amber, Green) |

---

## 10. References & Technical Authority

1. **Ableton Reference Manual (Chapter: "Using Push 1")**: Official hardware reference for setup, pad modes, drum sequencing, scales, device racks, and session workflows. [Ableton Manual](https://www.ableton.com/en/manual/using-push-1/).
2. **Ableton Push 1 Learning Hub & Support**: Getting started, drum sequencing, and video documentation. [Ableton Learn Push](https://www.ableton.com/en/help/learn-push-1/).
3. **Carillon Audio: Ableton Push Tips & Hidden Tricks (Live 9.1.4)**: Hidden hardware shortcuts, drum parameter batch editing, single-drum quantize/delete, and momentary workflow modifiers. [Carillon Audio Push Tips](https://carillonaudio.wordpress.com/2015/08/03/ableton-push-tips-hidden-tricks-9-1-4/).
4. **Gluon Decompiled Ableton Live 9 Remote Scripts**: Primary technical authority for internal button CCs, SysEx line protocols, and scale lookup matrices. [`gluon/AbletonLive9_RemoteScripts/Push`](https://github.com/gluon/AbletonLive9_RemoteScripts/tree/master/Push).
5. **mc-zynthian Project Documentation & Implementation**:
   - Push 1 Technical Protocols & MIDI Architecture: [`docs/push-protocols.md`](push-protocols.md)
   - Push 1 Standalone Python Driver & Zynthian `ctrldev`: [`scripts/pushy.py`](../scripts/pushy.py)
   - Roland MC-101 Guide: [`docs/mc101-guide.md`](mc101-guide.md)
   - Roland MC-101 SysEx & Memory Architecture: [`docs/mc101-sysex.md`](mc101-sysex.md)
   - Pisound Guide: [`docs/pisound-guide.md`](pisound-guide.md)
   - Korg nanoKONTROL Guide: [`docs/nanokontrol-guide.md`](nanokontrol-guide.md)
   - Macro Keyboard Guide: [`docs/macrokeyboard-guide.md`](macrokeyboard-guide.md)

