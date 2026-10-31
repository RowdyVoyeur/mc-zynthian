# Teensy 4.1 Hardware Architecture, Headless Synth & Co-Processor Bible

Comprehensive technical reference, headless USB architecture guide, and integration manual for repurposing the **Teensy 4.1 microcontroller** within the **`mc-zynthian`** ecosystem (Stage 3).

This document serves as the technical authority for integrating the Teensy 4.1 solely over its **high-speed USB connection to the Raspberry Pi 4—requiring zero additional hardware shields, breakout boards, breadboards, or external components**.

---

## 1. Executive Hardware Overview & USB Architecture

The **PJRC Teensy 4.1** is one of the most capable microcontroller development boards in existence, powered by the **NXP i.MXRT1062 ARM Cortex-M7** processor running at a baseline clock frequency of **$600\text{ MHz}$** (overclockable up to $816\text{ MHz} - 1.0\text{ GHz}$).

```
+---------------------------------------------------------------------------------+
|                               TEENSY 4.1 HARDWARE ARCHITECTURE                  |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                  NXP i.MXRT1062 ARM CORTEX-M7 @ 600 MHz                 |   |
|   |         (32KB L1I / 32KB L1D Cache / Hardware FPU Double Precision)     |   |
|   |         1024 KB On-Chip Tightly Coupled RAM (ITCM / DTCM)               |   |
|   |         7936 KB High-Speed Flash Memory (Encrypted/Execute-in-Place)    |   |
|   +-------------------------------------------------------------------------+   |
|                                       |                                         |
|      +--------------------------------+--------------------------------+        |
|      |                                                                 |        |
|      v                                                                 v        |
|  [MicroSD Card Socket]                                       [USB 2.0 High-Speed]
|  (Onboard 4-bit SDIO Bus                                     (480 Mbit/s Physical
|   Up to 25 MB/s Read IOPS)                                    Micro-B Interface)|
|                                                                        |        |
|                                                                        v        |
|                                                                 [RPi 4 USB Host]|
+---------------------------------------------------------------------------------+
```

### 1.1 Microcontroller Specifications
- **Processor:** NXP i.MXRT1062 (ARM Cortex-M7) with hardware dual-issue superscalar pipeline and Branch Target Address Cache.
- **Clock Speed:** $600\text{ MHz}$ (producing approximately $1,200\text{ CoreMark}$ benchmark throughput).
- **Floating-Point Unit (FPU):** Hardware single and double-precision floating-point acceleration (IEEE 754).
- **Memory Hierarchy:**
  - **RAM:** $1024\text{ KB}$ ($1\text{ MB}$) total RAM divided into:
    - **$512\text{ KB}$ Tightly Coupled Memory (ITCM / DTCM):** Single-cycle access @ $600\text{ MHz}$ for real-time DSP inner loops.
    - **$512\text{ KB}$ RAM2 (AXI Bus):** High-speed buffer memory for DMA and USB transfers.
  - **Flash:** $8\text{ MB}$ ($7936\text{ KB}$) Flash memory.
  - **Mass Storage:** Built-in MicroSD card slot connected via 4-bit SDIO bus.
- **Physical USB Interface:** Native **USB 2.0 High-Speed ($480\text{ Mbps}$)** controller with integrated PHY.

### 1.2 The "Zero-Extra-Parts" USB Constraint

In the `mc-zynthian` custom enclosure ([`assets/case-assembly.stl`](../assets/case-assembly.stl)), the Teensy 4.1 is mounted internally and connected to the Raspberry Pi 4 **solely via a standard USB cable**. There are no external audio breakout boards (such as the Teensy Audio Board Rev D), no soldered potentiometers, and no external I2C/SPI displays.

To operate without extra parts, the Teensy utilizes the class-compliant Teensy USB Composite Stack:
1. **USB Audio Class 1.0 / 2.0:** Using `AudioInputUSB` and `AudioOutputUSB` from the official Teensy Audio Library. The Teensy functions as a class-compliant bidirectional stereo soundcard:
   - **Audio OUT (Teensy $\to$ RPi):** 16-bit / 44.1 kHz or 24-bit / 48 kHz stereo digital audio streamed directly across the USB bus into ALSA and JACK.
   - **Audio IN (RPi $\to$ Teensy):** Stereo digital audio sent from Zynthian into Teensy for external DSP processing.
2. **USB Class-Compliant MIDI:** Using `usbMIDI`, providing up to 16 virtual MIDI cables with sub-microsecond packet latency and zero jitter.
3. **USB CDC Serial:** High-speed virtual COM port running at up to $480\text{ Mbps}$ for terminal debugging and firmware management.

---

## 2. The Architectural Reality: What Makes Sense on Teensy?

A critical design consideration in `mc-zynthian` is eliminating redundant software layers and avoiding sub-optimal workarounds:
> [!NOTE]
> **Zynthian's Existing Strengths:**
> - **Internal Synthesis:** The Raspberry Pi 4 running Zynthian Vangelis ([`docs/zynthian-guide.md`](zynthian-guide.md)) already hosts top-tier synth engines: **Pianoteq 8** (physical modeled pianos), **Surge-XT** (hybrid subtractive/wavetable), **Dexed** (6-op FM), **OB-Xd** (Oberheim analog emulation), and **Fluidsynth** (gigabyte soundfonts).
> - **Sequencing & Composition:** Zynthian Vangelis features an integrated **Step Sequencer (Zynseq)**, launcher clip matrix, and phrase/scene automation, giving you full clip launching and step sequencing without third-party tracker software.
> - **Audio Latency:** Zynthian runs directly on the Blokas Pisound via hardware I2S master clocks at an ultra-low processing period deadline of $1.33\text{ ms}$ and $\approx 5\text{ ms}$ round-trip latency ($64\text{ frames} @ 48\text{ kHz}$).
> 
> Therefore, running any tool that requires heavy host-side desktop wrappers, graphical screen scrapers, or complicated dependency stacks is an anti-pattern. The Teensy must operate as a **pure class-compliant USB device** that plugs directly into Zynthian's native ALSA/JACK and MIDI subsystem.

### 2.1 Criteria for an Ideal Teensy Role
To deliver genuine musical utility without adding parts:
1. **Zero Linux Host Dependencies:** The Teensy must enumerate as standard USB MIDI and/or USB Audio. Zero custom clients, zero GUI bridge daemons, and zero screen forwarding on the Raspberry Pi.
2. **Dedicated Vintage Hardware Emulation:** Act as an immutable, dedicated virtual-analog instrument (e.g. Minimoog Model D) whose parameters are mapped 1:1 to external hardware knobs on the nanoKONTROL or Push 1.
3. **Sub-Microsecond Hardware Timing Precision:** Leverage hardware 32-bit timer interrupts to generate jitter-free master MIDI clocks, Euclidean polyrhythms, or generative sequencing that multitasking Linux kernels cannot achieve.
4. **Standalone Hardware DSP Effects:** Function as an external hardware stereo insert effect over USB audio.

---

## 3. The Three Strategic Implementation Roles

```mermaid
flowchart TD
    subgraph TeensyHardware["Teensy 4.1 (600 MHz ARM Cortex-M7 over USB)"]
        USB_STACK["Class-Compliant USB Stack\n(Audio Class + USB MIDI + USB Serial)"]
    end

    subgraph ThreeRoles["Three Strategic Zero-Dependency Roles"]
        Role1["Role 1: Headless Mini-Teensy-Synth\n(Dedicated 6-Voice Minimoog Model D Voice)"]
        Role2["Role 2: Micro-Timing Algorithmic Engine\n(Euclidean Polyrhythms & Jitter-Free MIDI Clock)"]
        Role3["Role 3: Real-Time Granular DSP Insert\n(Hardware Lo-Fi Tape / Grain Freeze FX)"]
    end

    TeensyHardware --> Role1
    TeensyHardware --> Role2
    TeensyHardware --> Role3

    Role1 -->|USB Audio + USB MIDI CC| RPi["Raspberry Pi 4 (Zynthian Vangelis)"]
    Role2 -->|Pure USB MIDI (Zero Latency)| RPi
    Role3 -->|Stereo USB Audio Send/Return| RPi
```

---

## 4. Role 1: Headless Mini-Teensy-Synth (Nick Culbertson Minimoog Voice)

### 4.1 Architecture & Adapting to Zero Extra Parts

The **Mini-Teensy-Synth** ([NickCulbertson/Mini-Teensy-Synth](https://github.com/NickCulbertson/Mini-Teensy-Synth)) is a 6-voice polyphonic virtual-analog synthesizer inspired by the **Minimoog Model D**:
- **3 Oscillators per voice** (18 total oscillators running in real-time).
- **24dB Moog-style Ladder Filter** (`AudioFilterLadder` from the Teensy Audio Library).
- Dedicated Filter and Amp ADSR envelopes.
- Multi-waveform LFO with pitch, filter, and amp modulation destinations.

In its original form, the project requires 20 hardware potentiometers and a 16x2 LCD display. By stripping out the physical controls and adapting the firmware for **Headless USB Mode**, the Teensy becomes a dedicated, zero-latency Minimoog hardware synthesizer module controlled entirely via **USB MIDI CC** from Zynthian, the Korg nanoKONTROL, or Ableton Push 1.

```
+---------------------------------------------------------------------------------+
|                       HEADLESS MINI-TEENSY-SYNTH ARCHITECTURE                   |
|                                                                                 |
|  [USB MIDI IN from Zynthian / Push 1 / nanoKONTROL]                             |
|          |                                                                      |
|          v                                                                      |
|  [usbMIDI CC Dispatcher] ---> Maps 24 Minimoog Parameters                       |
|          |                                                                      |
|          v                                                                      |
|  +-------------------------------------------------------------------------+    |
|  |             6-VOICE POLYPHONIC VIRTUAL ANALOG AUDIO ENGINE              |    |
|  |  Voice 1..6: [Osc 1] [Osc 2] [Osc 3] [Noise]                            |    |
|  |                    |                                                    |    |
|  |                    v                                                    |    |
|  |             [24dB Moog Ladder Filter (AudioFilterLadder)]               |    |
|  |                    |                                                    |    |
|  |                    v                                                    |    |
|  |             [Dual ADSR Envelopes + LFO + Saturation]                    |    |
|  +-------------------------------------------------------------------------+    |
|          |                                                                      |
|          v                                                                      |
|  [AudioOutputUSB audioOutput] ---> Streams Stereo 16-bit 44.1kHz Audio          |
|          |                                                                      |
|          v                                                                      |
|  [RPi 4 USB Audio Host Interface (hw:TeensyAudio)]                              |
+---------------------------------------------------------------------------------+
```

### 4.2 Complete MIDI CC Implementation Map for Headless Operation

By removing the 20 physical potentiometers, every synth parameter is controlled via standard MIDI CC:

| Parameter Name | MIDI CC # | Value Range | Functional Description |
|---|---|---|---|
| **Oscillator 1 Waveform** | `CC 14` | $0 - 5$ | 0=Saw, 1=Square, 2=Triangle, 3=Sine, 4=Var-Tri, 5=Pulse |
| **Oscillator 2 Waveform** | `CC 15` | $0 - 5$ | 0=Saw, 1=Square, 2=Triangle, 3=Sine, 4=Var-Tri, 5=Pulse |
| **Oscillator 2 Octave** | `CC 16` | $0 - 4$ | Octave transpose: -2, -1, 0, +1, +2 |
| **Oscillator 2 Detune** | `CC 17` | $0 - 127$ | Fine pitch detune ($\pm 50\text{ cents}$) |
| **Oscillator 3 Waveform** | `CC 18` | $0 - 5$ | 0=Saw, 1=Square, 2=Triangle, 3=Sine, 4=Var-Tri, 5=Pulse |
| **Oscillator 3 Octave** | `CC 19` | $0 - 4$ | Octave transpose: -2, -1, 0, +1, +2 |
| **Oscillator 3 Detune** | `CC 20` | $0 - 127$ | Fine pitch detune ($\pm 50\text{ cents}$) |
| **Mixer: Osc 1 Level** | `CC 21` | $0 - 127$ | Oscillator 1 volume in mixer stage |
| **Mixer: Osc 2 Level** | `CC 22` | $0 - 127$ | Oscillator 2 volume in mixer stage |
| **Mixer: Osc 3 Level** | `CC 23` | $0 - 127$ | Oscillator 3 volume in mixer stage |
| **Mixer: Noise Level** | `CC 24` | $0 - 127$ | White/Pink noise generator volume |
| **Filter Cutoff** | `CC 74` | $0 - 127$ | 24dB Moog ladder filter cutoff frequency ($20\text{ Hz} - 18\text{ kHz}$) |
| **Filter Resonance** | `CC 71` | $0 - 127$ | Ladder filter feedback (self-oscillation capable) |
| **Filter Keyfollow** | `CC 25` | $0 - 127$ | Keyboard tracking coefficient ($0\% - 100\%$) |
| **Filter Env Amount** | `CC 26` | $0 - 127$ | Modulation depth of the filter ADSR |
| **Filter Attack** | `CC 27` | $0 - 127$ | Filter envelope attack time ($1\text{ ms} - 5\text{ s}$) |
| **Filter Decay** | `CC 28` | $0 - 127$ | Filter envelope decay time ($5\text{ ms} - 10\text{ s}$) |
| **Filter Sustain** | `CC 29` | $0 - 127$ | Filter envelope sustain level ($0\% - 100\%$) |
| **Filter Release** | `CC 30` | $0 - 127$ | Filter envelope release time ($5\text{ ms} - 10\text{ s}$) |
| **Amp Attack** | `CC 73` | $0 - 127$ | Amplitude envelope attack time ($1\text{ ms} - 5\text{ s}$) |
| **Amp Decay** | `CC 75` | $0 - 127$ | Amplitude envelope decay time ($5\text{ ms} - 10\text{ s}$) |
| **Amp Sustain** | `CC 79` | $0 - 127$ | Amplitude envelope sustain level ($0\% - 100\%$) |
| **Amp Release** | `CC 72` | $0 - 127$ | Amplitude envelope release time ($5\text{ ms} - 10\text{ s}$) |
| **LFO Rate** | `CC 76` | $0 - 127$ | Low frequency oscillator rate ($0.1\text{ Hz} - 30\text{ Hz}$) |
| **LFO Amount** | `CC 77` | $0 - 127$ | Modulation depth to assigned destination |
| **Glide (Portamento)** | `CC 5` | $0 - 127$ | Pitch transition time between legato notes |

### 4.3 Headless Firmware Implementation Sketch (`MiniTeensyHeadless.ino`)

```cpp
#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

// Audio pipeline: 3 Oscillators + Noise -> Mixer -> Moog Ladder Filter -> Envelope -> USB Audio
AudioSynthWaveform       osc1_1;
AudioSynthWaveform       osc2_1;
AudioSynthWaveform       osc3_1;
AudioSynthNoiseWhite     noise_1;
AudioMixer4              voice1_mixer;
AudioFilterLadder        ladder_filter1;
AudioEffectEnvelope      amp_envelope1;
AudioMixer4              master_mixer;
AudioOutputUSB           usb_audio; // Class-compliant USB audio output!

AudioConnection          patchCord1(osc1_1, 0, voice1_mixer, 0);
AudioConnection          patchCord2(osc2_1, 0, voice1_mixer, 1);
AudioConnection          patchCord3(osc3_1, 0, voice1_mixer, 2);
AudioConnection          patchCord4(noise_1, 0, voice1_mixer, 3);
AudioConnection          patchCord5(voice1_mixer, 0, ladder_filter1, 0);
AudioConnection          patchCord6(ladder_filter1, 0, amp_envelope1, 0);
AudioConnection          patchCord7(amp_envelope1, 0, master_mixer, 0);
AudioConnection          patchCord8(master_mixer, 0, usb_audio, 0); // Left channel
AudioConnection          patchCord9(master_mixer, 0, usb_audio, 1); // Right channel

void handleControlChange(byte channel, byte control, byte value) {
    switch (control) {
        case 74: // Filter Cutoff
            {
                float freq = 20.0f * powf(900.0f, (float)value / 127.0f);
                ladder_filter1.frequency(freq);
            }
            break;
        case 71: // Filter Resonance
            ladder_filter1.resonance((float)value / 127.0f * 1.15f);
            break;
        case 73: // Amp Attack
            amp_envelope1.attack((float)value * 25.0f); // 0 to 3175 ms
            break;
        case 75: // Amp Decay
            amp_envelope1.decay((float)value * 40.0f);
            break;
        case 79: // Amp Sustain
            amp_envelope1.sustain((float)value / 127.0f);
            break;
        case 72: // Amp Release
            amp_envelope1.release((float)value * 50.0f);
            break;
        default:
            break;
    }
}

void handleNoteOn(byte channel, byte note, byte velocity) {
    if (velocity > 0) {
        float noteFreq = 440.0f * powf(2.0f, (float)(note - 69) / 12.0f);
        osc1_1.frequency(noteFreq);
        osc2_1.frequency(noteFreq * 1.002f); // subtle detune
        osc3_1.frequency(noteFreq * 0.5f);   // sub octave
        amp_envelope1.noteOn();
    } else {
        amp_envelope1.noteOff();
    }
}

void handleNoteOff(byte channel, byte note, byte velocity) {
    amp_envelope1.noteOff();
}

void setup() {
    AudioMemory(40);

    // Initialize waveforms
    osc1_1.begin(WAVEFORM_SAWTOOTH);
    osc2_1.begin(WAVEFORM_SQUARE);
    osc3_1.begin(WAVEFORM_TRIANGLE);

    voice1_mixer.gain(0, 0.3f);
    voice1_mixer.gain(1, 0.3f);
    voice1_mixer.gain(2, 0.3f);
    voice1_mixer.gain(3, 0.0f);

    ladder_filter1.frequency(2500);
    ladder_filter1.resonance(0.3);

    // Bind USB MIDI callbacks
    usbMIDI.setHandleControlChange(handleControlChange);
    usbMIDI.setHandleNoteOn(handleNoteOn);
    usbMIDI.setHandleNoteOff(handleNoteOff);
}

void loop() {
    // Process incoming USB MIDI events with microsecond polling
    usbMIDI.read();
}
```

### 4.4 Integrating into Zynthian as an External Instrument Chain
Once flashed, the Teensy enumerates as a USB soundcard (`hw:TeensyAudio`) and a USB MIDI port.
To integrate into Zynthian:
1. In the Zynthian Main Mixer, add an **Audio Chain -> Audio In** to capture the Teensy's USB audio.
2. In **MIDI Options**, route the desired sequencer track or MIDI controller to the Teensy USB MIDI port.
3. Map the Korg nanoKONTROL faders to CC 74 (Cutoff), CC 71 (Resonance), CC 73 (Attack), CC 72 (Release) for instant tactile control.

---

## 5. Role 2: Micro-Timing Algorithmic MIDI Co-Processor

### 5.1 The Jitter Reality in Linux Audio
Even with an optimized Linux `PREEMPT_RT` real-time kernel, multitasking operating systems suffer from process scheduling latency, timer interrupt coalescing, and CPU cache misses. Hardware MIDI jitter on a Raspberry Pi typically ranges between **$50\mu\text{s}$ and $250\mu\text{s}$**.

In contrast, the Teensy 4.1's Cortex-M7 features dedicated hardware 32-bit timers (`IntervalTimer`) capable of executing interrupt service routines with **sub-microsecond precision ($< 2\mu\text{s}$)**.

```
+---------------------------------------------------------------------------------+
|                       MICRO-TIMING ALGORITHMIC MIDI ENGINE                      |
|                                                                                 |
|  [Hardware IntervalTimer (1.0 microsecond resolution)]                          |
|          |                                                                      |
|          v                                                                      |
|  [Algorithmic Generative Engines]                                               |
|  +-------------------------------------------------------------------------+    |
|  | Track 1: Euclidean Rhythm Generator E(k, n) -> E(5, 16)                 |    |
|  | Track 2: Euclidean Rhythm Generator E(k, n) -> E(7, 12) (Polyrhythm)   |    |
|  | Track 3: Turing Machine (Shift register generative melodies)           |    |
|  | Track 4: Chord Inversion Engine (Dynamic voice leading)                 |    |
|  +-------------------------------------------------------------------------+    |
|          |                                                                      |
|          v                                                                      |
|  [usbMIDI Virtual Cable 1]                     [usbMIDI Virtual Cable 2]        |
|          |                                                 |                    |
|          v                                                 v                    |
|  [RPi Zynthian Internal Synths]                [Roland MC-101 Hardware Tracks]  |
|  (Pianoteq / Dexed / Surge-XT)                 (4 Independent Stems via USB)    |
+---------------------------------------------------------------------------------+
```

### 5.2 Generative Capabilities with Zero Audio Overhead
- **Four Euclidean Rhythmic Streams:** Generates interlocking mathematical polyrhythms (e.g. $E(5, 16)$ vs $E(7, 12)$) synchronized with incoming MIDI clock.
- **Turing Machine / Shift Register Melodies:** Generates looping, mutating algorithmic melodies that slowly evolve over time.
- **Zero Latency & Zero CPU Load:** Uses pure USB MIDI; does not consume audio buffers or require ALSA audio bridges.

---

## 6. Role 3: Real-Time Granular / Lo-Fi Audio Insert Processor

In this role, the Teensy 4.1 functions as an **external hardware stereo effects processor**:
- Zynthian routes an audio track or aux send over USB to the Teensy (`AudioInputUSB`).
- The Teensy executes real-time DSP using the Teensy Audio Library:
  - `AudioEffectGranular`: Real-time pitch-shifting, grain freeze, and time-stretching.
  - `AudioEffectWaveshaper`: Analog saturation and tube-style overdrive.
  - `AudioFilterStateVariable`: High-resonance bandpass and notch filters.
- The wet audio returns to Zynthian (`AudioOutputUSB`) with zero analog conversion noise.

---

## 7. Firmware Development & Flashing Workflow (External Workstation)

To keep the Raspberry Pi 4 operating system fast, uncluttered, and strictly dedicated to real-time audio performance, **no build tools, compilers, or flashing utilities are installed on ZynthianOS**. 

All firmware development, code compilation, and hardware flashing are performed externally on a separate workstation (e.g. running Linux Mint) using standard Teensy tools. Once programmed, the Teensy 4.1 is connected to the Raspberry Pi 4 solely as an autonomous, class-compliant USB peripheral.

### 7.1 Workstation Build Configuration (Arduino IDE / Teensyduino)

When compiling firmware for any of the zero-dependency roles on your development machine, configure the following settings under the **Tools** menu:

- **Board:** `Teensy 4.1`
- **USB Type:** `Serial + MIDI + Audio`
  - *Why this is critical:* This setting automatically activates the Teensy USB composite descriptor, linking `usbMIDI`, `AudioInputUSB`, `AudioOutputUSB`, and CDC Serial. When connected to the Pi, Linux automatically binds native ALSA audio and MIDI drivers without needing third-party drivers or host software.
- **CPU Speed:** `600 MHz`
- **Optimize:** `Faster` (or `Fastest`)

> [!NOTE]
> **Linux Workstation Udev Rules:**
> If programming on a Linux host (such as Linux Mint), ensure the standard PJRC udev rules (`00-teensy.rules` from [pjrc.com/teensy/00-teensy.rules](https://www.pjrc.com/teensy/00-teensy.rules)) are installed in `/etc/udev/rules.d/` on that development machine so non-root users can flash the microcontroller.

### 7.2 Flashing & Connecting to Zynthian

1. Flash the sketch (e.g., `MiniTeensyHeadless.ino`) to the Teensy 4.1 on your development workstation.
2. Disconnect the Teensy from the workstation and plug it into a USB port on the `mc-zynthian` Raspberry Pi 4.
3. On the Raspberry Pi, Zynthian immediately enumerates the Teensy as a standard class-compliant USB audio interface and MIDI port. Zero configuration or terminal commands are required on the Pi.

---

## 8. Comparative Decision Matrix & Strategic Recommendation

| Evaluation Criteria | Role 1: Headless Mini-Teensy-Synth | Role 2: Micro-Timing Algorithmic Engine | Role 3: Real-Time Granular DSP Insert |
|---|---|---|---|
| **Primary Value** | Dedicated 6-voice Minimoog Model D | Jitter-free Euclidean polyrhythms | Hardware stereo insert effect |
| **RPi CPU Overhead** | **Zero** (100% on Teensy) | **Zero** | **Zero** |
| **Host Dependencies** | **None** (Class-compliant USB) | **None** (Class-compliant USB MIDI) | **None** (Class-compliant USB Audio) |
| **Audio Latency** | $\approx 2.9\text{ ms}$ (USB audio) | **$0\text{ ms}$ (No audio delay; pure MIDI)** | $\approx 5.8\text{ ms}$ (Round-trip USB send/return) |
| **Tactile Usability** | Exceptional via nanoKONTROL / Push 1 CCs | Set-and-forget generative sync | Real-time knob mangling |
| **Sonic Character** | 24dB Moog Ladder Analog warmth | Generative mathematical rhythms | Lo-fi tape & granular texture |

### Strategic Recommendation

> [!TIP]
> **The Optimal Path Forward:**
> 1. **Primary Recommendation (Role 1 — Headless Mini-Teensy-Synth):** 
>    If you want an extra dedicated, hands-on analog synthesizer voice whose filter cutoff, resonance, and envelopes map 1:1 to the Korg nanoKONTROL faders and Push 1 encoders, the headless adaptation of Nick Culbertson's Minimoog code is the cleanest fit. It requires **zero custom software on Zynthian**—it simply appears as a class-compliant USB synth.
> 2. **Alternative Recommendation (Role 2 — Micro-Timing Algorithmic MIDI Engine):**
>    If you prefer to keep all audio processing internal to Zynthian and avoid USB audio streaming altogether, turn the Teensy into an ultra-tight Euclidean polyrhythm and generative MIDI co-processor. It generates mathematical grooves with sub-microsecond precision, firing note triggers into Zynthian and the Roland MC-101 simultaneously with **zero audio buffer latency**.
