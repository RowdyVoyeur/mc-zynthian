# Blokas Pisound on Zynthian: Installation, Configuration & Operations Bible

Comprehensive hardware reference, low-latency tuning guide, and operational manual for integrating the **Blokas Pisound** soundcard and MIDI interface into the **Zynthian OS** (Raspberry Pi 4 / Blokas Pisound / Custom DIY Enclosure).

This document serves as the technical authority for Stage 1 of the [`mc-zynthian`](../README.md) roadmap, ensuring studio-grade audio quality, ultra-low latency matching or exceeding Blokas Patchbox OS benchmarks, dedicated 5-pin DIN MIDI communication, and multi-gesture control via **The Button**. For full hardware specifications, bill of materials, and enclosure assembly, see [`docs/rpi-specs.md`](rpi-specs.md) and [`assets/case-assembly.stl`](../assets/case-assembly.stl).

---

## 1. Hardware Overview & Technical Architecture

The **Blokas Pisound** is an ultra-low-latency soundcard and MIDI interface designed specifically for the Raspberry Pi 40-pin GPIO header.

```
                  +-------------------------------------------------------------+
                  |  [Input Gain Pot]              [Output Volume Pot]          |
                  |  (0 dB to +40 dB)              (Master Analog Attenuator)   |
                  |                                                             |
                  |  (O) 1/4" Stereo Input         (O) 1/4" Stereo Output       |
                  |      [Peak LED]                    [Volume LED]             |
                  |                                                             |
+-----------------+                                                             +-----------------+
| (:::) DIN IN    |  [PCM1804 ADC]                 [PCM5102A DAC]               | (:::) DIN OUT   |
| Opto-Isolated   |  24-bit / 192 kHz              32-bit / 384 kHz             | High-Speed      |
| 5-Pin MIDI      |                                                             | 5-Pin MIDI      |
+-----------------+  [Dual Low-Jitter Oscillators] [SPI MIDI Transceiver]       +-----------------+
                  |  22.5792 MHz / 24.576 MHz      (Jitter-Free DIN Clocking)   |
                  |                                                             |
                  |  [The Button] (GPIO 17)        [40-Pin Raspberry Pi Header] |
                  +-------------------------------------------------------------+
```

### 1.1 Audio Conversion Subsystem
- **Digital-to-Analog Converter (DAC)**: Texas Instruments / Burr-Brown **PCM5102A**:
  - Resolution: Up to $32\text{-bit}$ PCM.
  - Dynamic Range / Signal-to-Noise Ratio (SNR): $112\text{ dB}$.
  - Total Harmonic Distortion + Noise ($\text{THD+N}$): $-93\text{ dB}$ ($@ -1\text{ dBFS}$).
  - Integrated high-performance charge pump generates an internal negative supply rail, enabling true ground-centered $2.1\text{V}_\text{RMS}$ line-level outputs without bulky DC-blocking capacitors.
- **Analog-to-Digital Converter (ADC)**: Texas Instruments / Burr-Brown **PCM1804**:
  - Resolution: Up to $24\text{-bit}$ PCM.
  - Dynamic Range / SNR: $102\text{ dB}$.
  - $\text{THD+N}$: $-96\text{ dB}$.
  - Fully differential analog front end with integrated anti-aliasing decimation filter.
- **Dual Low-Jitter Master Clock Oscillators**:
  - Unlike consumer soundcards that derive I2S audio clocks from the Raspberry Pi's internal PLL (which suffers from high jitter and fractional-divider noise), Pisound carries two onboard ultra-low-jitter quartz crystal oscillators:
    - **$22.5792\text{ MHz}$**: Dedicated master clock for multiples of $44.1\text{ kHz}$ ($44.1, 88.2, 176.4\text{ kHz}$).
    - **$24.5760\text{ MHz}$**: Dedicated master clock for multiples of $48.0\text{ kHz}$ ($48.0, 96.0, 192.0\text{ kHz}$).
  - Pisound operates in **I2S Master Mode**, driving the Raspberry Pi's I2S peripheral with clean, jitter-free bit-clock and frame-sync signals.

### 1.2 Analog Controls & Gain Staging
- **Input Gain Potentiometer**:
  - Continuously variable from **$0\text{ dB}$ (unity line level)** up to **$+40\text{ dB}$ (high gain)**.
  - Accommodates line-level synthesizers (e.g., Roland MC-101), dynamic microphones, electric guitars, and modular synthesizers.
- **Peak / Activity LED**:
  - Two-stage visual monitoring directly on the analog front-end:
    - **Green**: Signal presence (audio level $> -30\text{ dBFS}$).
    - **Red**: Clipping warning (audio level $\ge -3\text{ dBFS}$).
- **Output Volume Potentiometer**:
  - Analog stereo potentiometer placed directly *after* the DAC output stage.
  - Allows full-range headphone and monitor listening level attenuation in the analog domain, preserving **$100\%$ digital bit-depth and maximum dynamic range** without digital truncation.

### 1.3 MIDI Hardware Subsystem
- **5-Pin DIN MIDI Input**:
  - Fully opto-isolated using high-speed optical couplers, preventing ground loops and hum when interconnected with vintage or mains-powered synthesizers.
- **5-Pin DIN MIDI Output**:
  - High-speed buffered driver capable of transmitting dense MIDI streams, Clock, and System Exclusive (SysEx) dumps without data drops.
- **Hardware SPI-to-UART Transceiver**:
  - Pisound offloads MIDI serial communication from the Raspberry Pi's internal Broadcom UART to a dedicated onboard ATmega microcontroller communicating via high-speed SPI.
  - Completely eliminates standard Linux UART baud rate jitter ($31.25\text{ kbaud}$ clock mismatch on RPi).

### 1.4 Physical GPIO Pin Allocation & The Button
Pisound connects to the Raspberry Pi 40-pin header using the following pin assignments:

| Pin # | Broadcom GPIO | Hardware Function | Purpose |
|---|---|---|---|
| **Pin 12** | `GPIO 18` | `PCM_CLK` (I2S Bit Clock) | I2S Audio Clock (driven by Pisound) |
| **Pin 35** | `GPIO 19` | `PCM_FS` (I2S Frame Sync) | I2S Word Select / LRCLK |
| **Pin 38** | `GPIO 20` | `PCM_DIN` (I2S Data In) | Audio ADC capture data into Pi |
| **Pin 40** | `GPIO 21` | `PCM_DOUT` (I2S Data Out) | Audio DAC playback data from Pi |
| **Pin 19** | `GPIO 10` | `SPI_MOSI` | SPI Command & MIDI data to Pisound |
| **Pin 21** | `GPIO 9` | `SPI_MISO` | SPI Status & MIDI data from Pisound |
| **Pin 23** | `GPIO 11` | `SPI_SCLK` | SPI Serial Clock |
| **Pin 24** | `GPIO 8` | `SPI_CE0` | SPI Chip Select |
| **Pin 11** | `GPIO 17` | Input (Pull-Up) | **The Button** (Active-Low Hardware Switch) |
| **Pin 1, 17** | `3.3V` | DC Power Rail | Digital logic power |
| **Pin 2, 4** | `5.0V` | DC Power Rail | Analog rails and charge-pump power |
| **Pin 6, 9, 14, 20, 25, 30, 34, 39** | `GND` | Ground | System Ground |

> [!WARNING]
> **GPIO Conflicts in Custom Enclosures:**
> If you are wiring additional physical switches, encoders, or displays (e.g., custom macro keyboards, rotary encoders, or displays) to the remaining Raspberry Pi GPIO pins, **never connect any lines to GPIO 18, 19, 20, 21, 10, 9, 11, 8, or 17**. All remaining GPIO lines (such as GPIO 2, 3 for I2C, GPIO 4, 14, 15, 22, 23, 24, 27) remain free for user expansions.

---

## 2. Installing Pisound on Zynthian

### 2.1 Physical Installation (Raspberry Pi 4)
1. Ensure the Raspberry Pi 4 is powered off and disconnected from the power supply.
2. Secure the Raspberry Pi into your custom DIY base using $11\text{ mm}$ or $12\text{ mm}$ M2.5 brass standoffs.
3. Carefully align the Pisound's 40-pin female socket with the Raspberry Pi's 40-pin male GPIO header.
4. Press down evenly until the connector is firmly seated against the standoffs. Fasten the top M2.5 screws into the standoffs to prevent mechanical flex when plugging in heavy 1/4" audio cables.

### 2.2 Enabling the Soundcard via Zynthian Webconf
Zynthian OS natively includes the Pisound Linux ALSA kernel module (`snd-soc-pisound`) and device tree overlay.

1. Connect to Zynthian via a web browser on your local network:
   ```text
   https://zynthian.local
   ```
   *(or navigate to `http://<IP-ADDRESS>` using default credentials `raspberry` / `opensynth`).*
2. In the top navigation menu, go to **Hardware** $\rightarrow$ **Audio**.
3. Under **Soundcard**, select **`Pisound`** from the dropdown menu.
4. Click **Save** at the bottom of the page.
5. Zynthian will prompt you to reboot. Confirm and allow the system to restart.

```
+-----------------------------------------------------------------------+
| Hardware -> Audio Settings                                            |
|                                                                       |
| Soundcard:        [ Pisound                        ▼ ]                |
| Jack Sample Rate: [ 48000                          ▼ ]                |
| Jack Buffer Size: [ 128                            ▼ ]                |
| Jack Periods:     [ 2                              ▼ ]                |
+-----------------------------------------------------------------------+
```

### 2.3 Manual Verification via SSH
To verify that the soundcard overlay is loaded properly, open an SSH terminal to your Zynthian:

```bash
ssh root@zynthian.local
```

Inspect `/boot/firmware/config.txt` (or `/boot/config.txt` on older kernel releases):
```bash
grep pisound /boot/firmware/config.txt
```
The output should confirm:
```text
dtoverlay=pisound
```

Verify that ALSA recognizes both the audio codec and rawmidi endpoints:
```bash
aplay -l
arecord -l
amidi -l
```
You should see:
```text
card 1: pisound [pisound], device 0: PSND (24.576MHz) snd-soc-dummy-dai-0 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
...
Dir Device    Name
IO  hw:1,0    pisound MIDI PSND-XXXXX
```

### 2.4 Software Suite (Optional)
ZynthianOS includes native Linux kernel support and the ALSA driver for Pisound out of the box. No external software packages or additional repositories are needed for full audio and MIDI operation, or for mapping The Button natively in Webconf (see [Section 4.1](#41-native-zynthian-integration-recommended-clean--zero-clutter)).

If you specifically require the third-party Blokas multi-click daemon (`pisound-btn`) or `pisound-config` utilities:
```bash
# Optional: only install if using the pisound-btn multi-click daemon
curl https://blokas.io/apt-setup.sh | sh
apt-get update
apt-get install -y pisound-btn
```

---

## 3. Low-Latency Performance & Audio Optimization

Pisound's dual crystal oscillators and dedicated hardware converters deliver professional, jitter-free low-latency performance. Configuring JACK parameters correctly ensures pristine audio without buffer underruns (XRUNs).

### 3.1 Understanding Audio Latency Formulas
Real-time audio latency consists of three distinct mathematical metrics:

1. **JACK Period Deadline ($T_\text{deadline}$):**
   The time window the CPU has to synthesize or process a single audio block:
   $$T_\text{deadline} = \frac{\text{Buffer Size (Frames)}}{\text{Sample Rate (Hz)}} = \frac{64}{48000\text{ Hz}} \approx 1.333\text{ ms}$$
   *(Note: $1.33\text{ ms}$ is the processing period deadline, not the total round-trip latency).*

2. **Output Buffer Latency:**
   The delay between audio leaving the synthesis engine and emerging from the DAC with $n$ periods:
   $$\text{Latency}_{\text{output}} = \frac{n \times \text{Buffer Size (Frames)}}{\text{Sample Rate (Hz)}} = \frac{2 \times 64}{48000\text{ Hz}} \approx 2.667\text{ ms}$$

3. **Approximate Round-Trip Latency (Analog In $\rightarrow$ DSP $\rightarrow$ Analog Out):**
   Round-trip latency includes ADC capture buffers, the JACK scheduling cycle, DAC playback buffers, and hardware converter group delays (filter decimation/interpolation inside the PCM1804 ADC and PCM5102A DAC, $\approx 0.8\text{ ms} - 1.2\text{ ms}$ at $48\text{ kHz}$):
   $$\text{Latency}_{\text{round-trip}} \approx \frac{(n + 1) \times \text{Buffer Size}}{\text{Sample Rate}} + \text{Converter Group Delay}$$

| Sample Rate | Buffer Size | Periods | Period Deadline | Output Buffer | Approx. Round-Trip | Performance Profile |
|---|---|---|---|---|---|---|
| **$48000\text{ Hz}$** | **$64\text{ frames}$** | **$2$** | **$1.33\text{ ms}$** | **$2.67\text{ ms}$** | **$\approx 4.8 - 5.2\text{ ms}$** | **Ultra-Low Latency / Stage Solo Performance** |
| **$48000\text{ Hz}$** | **$128\text{ frames}$**| **$2$** | **$2.67\text{ ms}$** | **$5.33\text{ ms}$** | **$\approx 8.8 - 9.2\text{ ms}$** | **Recommended Stage Default (Rock-solid)** |
| **$48000\text{ Hz}$** | **$256\text{ frames}$**| **$2$** | **$5.33\text{ ms}$** | **$10.67\text{ ms}$**| **$\approx 16.8 - 17.2\text{ ms}$**| **Heavy Multitrack & Dense Multi-FX Chains** |
| **$44100\text{ Hz}$** | **$64\text{ frames}$** | **$2$** | **$1.45\text{ ms}$** | **$2.90\text{ ms}$** | **$\approx 5.3 - 5.7\text{ ms}$** | **Optimal for Stage 2 & 3 (MC-101 / Teensy Sync)** |
| **$44100\text{ Hz}$** | **$128\text{ frames}$**| **$2$** | **$2.90\text{ ms}$** | **$5.80\text{ ms}$** | **$\approx 9.6 - 10.0\text{ ms}$**| **Recommended Stage 2 & 3 Standard** |

> [!TIP]
> **Measuring True Round-Trip Latency:**
> To measure exact round-trip latency on your hardware unit down to the microsecond, connect a 1/4" patch cable between Pisound's Output and Input jacks and run the standard JACK utility:
> ```bash
> jack_iodelay
> ```

### 3.2 Sample Rate Strategy: 48 kHz vs 44.1 kHz
- **Stage 1 (Pisound Standalone):** Running JACK at **$48000\text{ Hz}$** is the standard default for Zynthian synth engines (ZynAddSubFX, Pianoteq, Fluidsynth) and provides slightly lower buffer latency.
- **Stage 2 & Stage 3 (Roland MC-101 & Teensy USB Audio):** **Switch Zynthian JACK to $44100\text{ Hz}$**.
  - The Roland MC-101 operates fixed at $44.1\text{ kHz}$ in USB vendor mode ([`docs/mc101-guide.md`](mc101-guide.md)).
  - Teensy 4.1 USB Audio runs fixed at 16-bit / $44.1\text{ kHz}$ ([`docs/teensy-guide.md`](teensy-guide.md)).
  - Pisound features a dedicated onboard **$22.5792\text{ MHz}$** quartz oscillator for native, zero-jitter $44.1\text{ kHz}$ operation.
  - Running JACK at $44.1\text{ kHz}$ eliminates continuous CPU-heavy sample-rate conversion (resampling) across all USB audio bridges, preventing drift artifacts and reducing CPU load.

### 3.3 Configuring JACK in Zynthian Webconf
1. Navigate to **Hardware** $\rightarrow$ **Audio** in Zynthian Webconf.
2. Set **Jack Sample Rate** to **`48000`** (Stage 1) or **`44100`** (Stages 2 & 3).
3. Set **Jack Buffer Size** to **`128`** (safe default) or **`64`** (ultra-low latency).
4. Set **Jack Periods** to **`2`**.
5. Click **Save** to restart JACK with the new settings.

### 3.3 Linux System & Kernel Tuning
Ensure Zynthian OS prioritizes real-time audio threads without CPU-throttling interruptions:

#### 1. Real-Time Audio Thread Limits
Verify that `/etc/security/limits.d/audio.conf` grants full real-time scheduling priority:
```text
@audio   -  rtprio     95
@audio   -  memlock    unlimited
@audio   -  nice      -19
```

#### 2. CPU Governor to `performance`
Dynamic frequency scaling introduces microsecond CPU stalls when stepping clock frequencies up or down, causing audible clicks ("XRUNs"). Lock all 4 cores of the Raspberry Pi 4 to maximum clock speed:

```bash
# Check current governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Set performance governor permanently
echo "performance" | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

In Zynthian Webconf, navigate to **Software** $\rightarrow$ **CPU Options** and ensure the **CPU Governor** is set to **`Performance`**.

#### 3. Disable Wi-Fi Power Management
Power-saving polling on the wireless chip causes periodic DPC/interrupt spikes. Disable power saving on `wlan0`:
```bash
iwconfig wlan0 power off
```

---

## 4. "The Button": Configuration & Zynthian Integration

The multi-function tactile pushbutton on Pisound (**The Button**) is wired to **GPIO 17** (Physical Pin 11) with an internal pull-up resistor. Pressing the button pulls GPIO 17 to ground (`Active-Low`).

There are two distinct methods to integrate The Button into Zynthian:
1. **Native Zynthian Hardware Switch (Recommended — Zero Extra Software)**
2. **`pisound-btn` Background Daemon (Optional — Multi-click Gestures)**

---

### 4.1 Native Zynthian Integration (Recommended: Clean & Zero-Clutter)

In accordance with the project rule to keep the Raspberry Pi free of unnecessary background packages, ZynthianOS provides built-in native support for GPIO pushbuttons without installing any external daemons or modifying third-party apt repositories.

Zynthian supports three distinct physical press gestures per switch:
- **Short Press:** Quick tap ($< 0.3\text{ s}$).
- **Bold Press:** Deliberate hold ($\approx 0.3\text{ s} - 1.2\text{ s}$).
- **Long Press:** Extended hold ($> 1.2\text{ s}$).

#### Step-by-Step Setup:
1. Open Zynthian Webconf: `https://zynthian.local`
2. Navigate to **Hardware** $\rightarrow$ **Wiring Layout**.
3. Under **Wiring Layout**, select **`Custom`** (or edit your existing custom profile).
4. Assign an available switch index (e.g. `Switch 4` or `Switch 1`) to pin **`17`** (GPIO 17, Active-Low).
5. Navigate to **Interface** $\rightarrow$ **UI Key Binding / Hardware Switch Actions**.
6. Map each gesture directly to a native Zynthian CUIA or MIDI action:
   - **Short Press:** `TOGGLE_AUDIO_PLAY` (or `TOGGLE_MIDI_PLAY`)
   - **Bold Press:** `SCREEN_AUDIO_MIXER`
   - **Long Press:** `ALL_NOTES_OFF` (Emergency MIDI Panic)
7. Click **Save** and restart UI.

This approach executes directly within Zynthian's event loop, requiring zero background daemons, zero external scripts, and zero additional memory overhead.

---

### 4.2 Alternative Approach: The `pisound-btn` Daemon (Multi-Click Gestures)

If you require advanced multi-click gestures (such as double-click, triple-click, or 5-second poweroff), you can install the official Blokas `pisound-btn` daemon:

```bash
# Optional: Install Blokas suite if multi-click gestures are required
curl https://blokas.io/apt-setup.sh | sh
apt-get update
apt-get install -y pisound-btn
```

#### Mapping via `/etc/pisound.conf`:
The `pisound-btn` daemon invokes shell scripts on detected clicks. Zynthian's UI can be commanded over local UDP OSC port **`1370`** using `oscsend`:

```text
# /etc/pisound.conf - Zynthian Pisound Button Action Mappings
CLICK_1       /usr/local/bin/zynthian_play.sh
CLICK_2       /usr/local/bin/zynthian_mixer.sh
CLICK_3       /usr/local/bin/zynthian_panic.sh
HOLD_5S       /usr/local/bin/zynthian_poweroff.sh
```

Example integration scripts:
```bash
# /usr/local/bin/zynthian_play.sh (Toggle Play)
oscsend 127.0.0.1 1370 /cuia/TOGGLE_AUDIO_PLAY

# /usr/local/bin/zynthian_mixer.sh (Jump to Mixer)
oscsend 127.0.0.1 1370 /cuia/SCREEN_AUDIO_MIXER

# /usr/local/bin/zynthian_panic.sh (All Notes Off)
oscsend 127.0.0.1 1370 /cuia/ALL_NOTES_OFF

# /usr/local/bin/zynthian_poweroff.sh (Safe Shutdown)
oscsend 127.0.0.1 1370 /cuia/POWER_OFF
```
*(Always verify available CUIA names in your Zynthian Webconf under **Interface -> UI Actions**).*

---

## 5. Operating Pisound on Zynthian

### 5.1 Calibrating Input Gain & The Peak LED
When feeding external audio into Zynthian (e.g., sampling from a microphone, processing an electric guitar through Guitarix, or passing the Roland MC-101 into Zynthian's master effects matrix):

1. Connect your audio source to the **Stereo 1/4" Input Jack**.
   - *Mono Source*: Use a standard TS 1/4" cable. The left channel receives signal; in Zynthian's audio router, duplicate In-L to both stereo channels.
   - *Stereo Source*: Use a TRS 1/4" stereo splitter cable ($1\times \text{TRS 1/4"} \rightarrow 2\times \text{TS 1/4"}$ or $3.5\text{ mm} \rightarrow \text{TRS 1/4"}$).
2. Start playing audio at maximum intended performance volume.
3. Observe the **Peak LED**:
   - Turn the **Input Gain Potentiometer** clockwise until the Peak LED flashes **Green** on rhythmic peaks.
   - If the LED flashes **Red**, the ADC is within $3\text{ dB}$ of clipping ($>-3\text{ dBFS}$). Back off the gain potentiometer counter-clockwise until red flashes cease completely.

### 5.2 Adjusting Analog Output Volume
- Connect your studio monitors, headphones, or mixer inputs to the **Stereo 1/4" Output Jack**.
- Leave Zynthian's digital Main Mixer fader (`zynmixer` Master Level) at **$0\text{ dB}$** ($100\%$).
- Adjust physical listening loudness strictly using Pisound's **Output Volume Potentiometer**.
- **Benefit**: Keeps DAC quantization noise floor at minimum and preserves the PCM5102A's entire $112\text{ dB}$ signal-to-noise ratio regardless of how quiet you listen!

### 5.3 Working with 5-Pin DIN MIDI
- Connect external MIDI hardware to Pisound's 5-Pin DIN ports:
  - **MIDI IN**: Connect to master keyboards or sequencers.
  - **MIDI OUT**: Connect to hardware synthesizers (e.g., Roland MC-101 or Teensy synth).
- In Zynthian UI:
  - Pisound's DIN MIDI port appears automatically in JACK MIDI routing as `pisound MIDI`.
  - In Zynthian's chain options, any synth layer can be bound to listen to `pisound MIDI` or transmit sequences generated by `zynseq` out through the DIN port.

### 5.4 Audio Routing Inside Zynthian UI
To route audio entering Pisound through Zynthian synth engines or effect chains:
1. On the Zynthian display (or webconf Audio Router), select **Audio In** (Capture 1 & 2).
2. Patch Capture 1/2 to the input of an Effect Chain (e.g., **MOD-UI**, **Guitarix Amp**, **Calf Studio Gear Reverb**, or **Pure Data Vocoder**).
3. Connect the output of the Effect Chain to the Main Audio Output (Playback 1 & 2).
4. Audio entering Pisound will now be processed in real time with imperceptible latency ($< 3\text{ ms}$).

---

## 6. Comprehensive Troubleshooting & Diagnostics

### 6.1 Diagnostic Commands Quick-Reference

Run these commands over SSH to diagnose issues with audio, MIDI, or button states:

| Diagnostic Goal | Command | Expected Healthy Output |
|---|---|---|
| Check ALSA Soundcard | `cat /proc/asound/cards` | `1 [pisound ]: pisound - pisound` |
| Check Audio Output Devices | `aplay -l` | `card 1: pisound [pisound], device 0: PSND...` |
| Check Audio Input Devices | `arecord -l` | `card 1: pisound [pisound], device 0: PSND...` |
| Check Raw MIDI Devices | `amidi -l` | `IO  hw:1,0  pisound MIDI PSND-XXXXX` |
| Check Device Tree Overlay | `grep pisound /boot/firmware/config.txt` | `dtoverlay=pisound` |
| Check Zynthian Service Status | `systemctl status zynthian` | `Active: active (running)` |
| Check Button Daemon Status (Optional) | `systemctl status pisound-btn` | `Active: active (running)` (if installed) |
| Test Button GPIO Pin State | `gpioget 0 17` | `1` (unpressed), `0` (pressed) |
| Monitor Real-Time DSP & XRUNs | `jack_cpu_load` (or `journalctl -u zynthian -f`) | Real-time CPU load and zero XRUN warnings |

---

### 6.2 Common Failure Modes & Solutions

#### Problem 1: No Audio Output / Soundcard Not Detected
- **Symptom**: `aplay -l` returns `no soundcards found` or only lists the internal bcm2835 headphone jack.
- **Root Cause**: The device tree overlay `dtoverlay=pisound` is missing or disabled in boot configuration.
- **Solution**:
  1. Open `/boot/firmware/config.txt` (or `/boot/config.txt`).
  2. Verify that `dtoverlay=pisound` is present and uncommented.
  3. Ensure `dtparam=audio=on` is disabled or commented out so the Pi does not prioritize the noisy internal audio jack.
  4. Reboot: `reboot`.

#### Problem 2: Audio Clicks, Pops, or Stuttering (XRUNs)
- **Symptom**: Audio crackles when playing chords or running heavy multi-effects; JACK logs report frequent `xrun` events.
- **Root Cause**: Buffer size is too aggressive ($64$ frames) for the current DSP load, or the CPU frequency governor is throttling down.
- **Solution**:
  1. Open Zynthian Webconf $\rightarrow$ **Hardware** $\rightarrow$ **Audio**.
  2. Increase **Jack Buffer Size** from `64` to **`128`** (or `256` for large multi-layer patches).
  3. Verify CPU governor: `echo "performance" | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`.
  4. Verify that Wi-Fi power saving is disabled: `iwconfig wlan0 power off`.

#### Problem 3: "The Button" Does Not Trigger Any Actions
- **Symptom**: Pressing The Button has no effect on Zynthian or system functions.
- **Root Cause**: `pisound-btn.service` is stopped, or GPIO 17 is conflicting with another configuration.
- **Solution**:
  1. Test physical switch connectivity: run `watch -n 0.1 gpioget 0 17` while holding The Button. The value must toggle from `1` to `0` when pressed.
  2. If the value does not toggle, inspect the physical connection and check for bent GPIO pins on Pin 11.
  3. Restart the service and inspect logs:
     ```bash
     systemctl restart pisound-btn
     journalctl -u pisound-btn -f
     ```
  4. Verify that the scripts mapped in `/etc/pisound.conf` exist and have execute permissions (`chmod +x`).

#### Problem 4: Severe Distortion or Harsh Buzzing on Audio In
- **Symptom**: Recorded or pass-through audio sounds heavily squared-off or digitally distorted.
- **Root Cause**: Input Gain potentiometer is set too high for a line-level instrument, causing ADC clipping ($0\text{ dBFS}$).
- **Solution**:
  1. Watch the **Peak LED** on Pisound.
  2. If the Peak LED is glowing solid red, turn the **Input Gain Pot** counter-clockwise until the LED blinks green only on maximum peaks.

#### Problem 5: Ground Loop Hum or High-Pitched Digital Whine
- **Symptom**: Low $50/60\text{ Hz}$ mains hum or high-pitched squealing that changes when the Raspberry Pi accesses the SD card or Wi-Fi.
- **Root Cause**: Ground loop formed between the Raspberry Pi power supply and connected external amplifiers/monitors, or using a noisy non-isolated USB switch-mode charger.
- **Solution**:
  1. Power the Raspberry Pi 4 using an official Raspberry Pi $15.3\text{W}$ USB-C power supply or an audiophile low-noise linear power supply.
  2. Use balanced audio cables or insert a 1:1 audio isolation transformer (DI box) between Pisound's 1/4" output and your studio monitors.
  3. Ensure the custom DIY enclosure grounds the Pisound mounting standoffs to chassis ground.

---

## 7. Complete Reference Documentation & Source Links

1. **Blokas Official Portal**: Hardware specifications, pinouts, and product architecture. [Blokas Pisound](https://blokas.io/pisound/).
2. **Blokas Pisound Documentation**: Official user guide, setup, and software documentation. [Blokas Pisound Docs](https://blokas.io/pisound/docs/).
3. **Blokas The Pisound Software Guide**: Detailed `pisound-btn`, `/etc/pisound.conf`, and `pisound-config` reference. [The Pisound Software](https://blokas.io/pisound/docs/the-pisound-software/).
4. **Blokas Pisound Kernel Driver & Daemon GitHub**: Driver source code, device tree overlay (`pisound.dts`), and `pisound-btn.c`. [`BlokasLabs/pisound`](https://github.com/BlokasLabs/pisound).
5. **Blokas Docs GitHub**: Markdown sources for Blokas documentation. [`BlokasLabs/pisound-docs`](https://github.com/BlokasLabs/pisound-docs).
6. **mc-zynthian Project Documentation & Ecosystem**:
   - Master Architecture & Stage Roadmap: [`README.md`](../README.md)
   - Push 1 Hardware Guide: [`docs/push-guide.md`](push-guide.md)
   - Push 1 Technical Protocols & MIDI Architecture: [`docs/push-protocols.md`](push-protocols.md)
   - Roland MC-101 Guide: [`docs/mc101-guide.md`](mc101-guide.md)
   - Roland MC-101 SysEx & Memory Architecture: [`docs/mc101-sysex.md`](mc101-sysex.md)
   - Korg nanoKONTROL Guide: [`docs/nanokontrol-guide.md`](nanokontrol-guide.md)
   - Macro Keyboard Guide: [`docs/macrokeyboard-guide.md`](macrokeyboard-guide.md)

