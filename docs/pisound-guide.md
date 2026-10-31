# Blokas Pisound on Zynthian: Installation, Configuration & Operations Bible

Comprehensive hardware reference, low-latency tuning guide, and operational manual for integrating the **Blokas Pisound** soundcard and MIDI interface into the **Zynthian OS** (Raspberry Pi 4 / Blokas Pisound / Custom DIY Enclosure).

This document serves as the technical authority for Stage 1 of the [`mc-zynthian`](../README.md) roadmap, ensuring studio-grade audio quality, ultra-low latency matching or exceeding Blokas Patchbox OS benchmarks, dedicated 5-pin DIN MIDI communication, and multi-gesture control via **The Button**.

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

### 2.4 Installing the Blokas Software Suite (`pisound-btn` & `pisound-config`)
To utilize **The Button** daemon and Blokas utilities within Zynthian's Debian-based environment, install the official Blokas repository packages:

```bash
# 1. Add Blokas APT repository and signing key
curl https://blokas.io/apt-setup.sh | sh

# 2. Update package lists
apt-get update

# 3. Install pisound daemon and configuration tools
apt-get install -y pisound pisound-btn pisound-config libgpiod-dev
```

Verify that the `pisound-btn` daemon is active:
```bash
systemctl status pisound-btn.service
```

---

## 3. Low-Latency Performance & Audio Optimization

Blokas Patchbox OS is renowned for achieving round-trip latency as low as $1.33\text{ ms}$. Zynthian OS can easily match or beat these numbers when configured correctly.

### 3.1 Understanding Audio Latency Formulas
Buffer latency is mathematically defined by the audio frame size, buffer periods, and sample rate:

$$\text{Latency}_{\text{buffer}} = \frac{\text{Buffer Size (Frames)} \times \text{Periods}}{\text{Sample Rate (Hz)}}$$

Round-trip latency (ADC input conversion $\rightarrow$ JACK processing $\rightarrow$ DAC output conversion) is:

$$\text{Latency}_{\text{round-trip}} = \frac{2 \times \text{Buffer Size} \times \text{Periods}}{\text{Sample Rate}} + \text{Hardware Converter Delay}$$

| Sample Rate | Buffer Size | Periods | Output Latency | Theoretical Round-Trip | Performance Profile |
|---|---|---|---|---|---|
| **$48000\text{ Hz}$** | **$64\text{ frames}$** | **$2$** | **$2.67\text{ ms}$** | **$\sim 4.2\text{ ms}$** | **Ultra-Low Latency / Stage Solo Performance** |
| **$48000\text{ Hz}$** | **$128\text{ frames}$**| **$2$** | **$5.33\text{ ms}$** | **$\sim 6.8\text{ ms}$** | **Recommended Studio Default (Rock-solid)** |
| **$48000\text{ Hz}$** | **$256\text{ frames}$**| **$2$** | **$10.67\text{ ms}$**| **$\sim 12.1\text{ ms}$**| **Heavy Multitrack & Dense Multi-FX Chains** |
| **$96000\text{ Hz}$** | **$64\text{ frames}$** | **$2$** | **$1.33\text{ ms}$** | **$\sim 2.5\text{ ms}$** | **Extreme Low Latency (Benchmark Matching)** |
| **$96000\text{ Hz}$** | **$128\text{ frames}$**| **$2$** | **$2.67\text{ ms}$** | **$\sim 3.8\text{ ms}$** | **High-Bandwidth Audiophile DSP** |

### 3.2 Configuring JACK in Zynthian Webconf
1. Go to **Hardware** $\rightarrow$ **Audio**.
2. Set **Jack Sample Rate** to **`48000`** (recommended standard for synth engines and Roland MC-101 sync) or **`96000`** (for minimum latency).
3. Set **Jack Buffer Size** to **`128`** (or **`64`** if using lighter synth engines like Pianoteq or Dexed).
4. Set **Jack Periods** to **`2`**.
5. Click **Save** and restart JACK.

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

```
+---------------------------------------------------------------------------------------------------+
| Single Click    (CLICK_1)  ---> Toggle Audio Routing / Toggle Playback (CUIA: TOGGLE_PLAY)        |
| Double Click    (CLICK_2)  ---> Switch Next Snapshot / Preset Bank (CUIA: NEXT_SNAPSHOT)         |
| Triple Click    (CLICK_3)  ---> MIDI Panic / All Notes Off (CUIA: ALL_NOTES_OFF)                  |
| Click 4+ Times  (OTHER)    ---> Toggle Master Mute (CUIA: TOGGLE_MUTE)                            |
| Hold 1s - 3s    (HOLD_1S)  ---> Jump to Mixer Screen (CUIA: SCREEN_MIXER)                         |
| Hold 3s - 5s    (HOLD_3S)  ---> Toggle Wi-Fi Hotspot / Network Access Point Mode                 |
| Hold 5s+        (HOLD_5S)  ---> Safe System Poweroff / Shutdown (systemctl poweroff)              |
+---------------------------------------------------------------------------------------------------+
```

### 4.1 Configuring the Button Daemon (`/etc/pisound.conf`)
The `pisound-btn` daemon continuously monitors GPIO 17, detects single clicks, double clicks, multi-clicks, and press-duration holds, and maps them to executable scripts.

Edit the configuration file:
```bash
nano /etc/pisound.conf
```

Configure the action bindings:
```text
# /etc/pisound.conf - Zynthian Pisound Button Action Mappings
DOWN          /usr/local/pisound/scripts/pisound-btn/system/down.sh
UP            /usr/local/pisound/scripts/pisound-btn/system/up.sh

# Clicks
CLICK_1       /usr/local/pisound/scripts/pisound-btn/zynthian_toggle_play.sh
CLICK_2       /usr/local/pisound/scripts/pisound-btn/zynthian_next_snapshot.sh
CLICK_3       /usr/local/pisound/scripts/pisound-btn/zynthian_panic.sh
CLICK_OTHER   /usr/local/pisound/scripts/pisound-btn/zynthian_toggle_mute.sh

CLICK_COUNT_LIMIT 8

# Holds
HOLD_1S       /usr/local/pisound/scripts/pisound-btn/zynthian_screen_mixer.sh
HOLD_3S       /usr/local/pisound/scripts/pisound-btn/toggle_wifi_hotspot.sh
HOLD_5S       /usr/local/pisound/scripts/pisound-btn/shutdown.sh
```

### 4.2 Integrating with Zynthian via CUIA (Callable UI Actions) & OSC
Zynthian exposes its entire user interface engine over **UDP OSC Port `1370`**. We can trigger any native UI action instantly from shell scripts using `oscsend` (included in Zynthian via `liblo-utils`).

Create the custom Zynthian integration scripts in `/usr/local/pisound/scripts/pisound-btn/`:

#### 1. Single Click: Toggle Play / Stop (`zynthian_toggle_play.sh`)
```bash
#!/bin/bash
# Toggle Zynthian Sequencer / Audio Playback
oscsend 127.0.0.1 1370 /cuia/toggle_play
```

#### 2. Double Click: Next Snapshot (`zynthian_next_snapshot.sh`)
```bash
#!/bin/bash
# Load next performance snapshot
oscsend 127.0.0.1 1370 /cuia/next_snapshot
```

#### 3. Triple Click: MIDI Panic / Silence (`zynthian_panic.sh`)
```bash
#!/bin/bash
# Send All Notes Off & reset all synth engines
oscsend 127.0.0.1 1370 /cuia/all_notes_off
```

#### 4. Hold 1s: Jump to Zynthian Mixer (`zynthian_screen_mixer.sh`)
```bash
#!/bin/bash
# Switch touchscreen display to Zynmixer view
oscsend 127.0.0.1 1370 /cuia/screen_mixer
```

#### 5. Make Scripts Executable & Restart Daemon
```bash
chmod +x /usr/local/pisound/scripts/pisound-btn/zynthian_*.sh
systemctl restart pisound-btn
```

### 4.3 Alternative Approach: Direct GPIO Switch in Zynthian Webconf
If you prefer not to run the background `pisound-btn` daemon, you can configure Zynthian's UI directly to read GPIO 17 as a hardware switch:

1. Open Zynthian Webconf: `https://zynthian.local`
2. Navigate to **Hardware** $\rightarrow$ **Wiring Layout**.
3. Select **`Custom`** wiring.
4. Under **Switches / Pushbuttons**, assign an unused switch action (e.g., `Switch 1` or `Select Button`) to **`GPIO 17`**.
5. Save and reboot. Zynthian's core UI thread will now read The Button natively.

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
| Check JACK Service Status | `systemctl status jack2` | `Active: active (running)` |
| Check Button Daemon Status | `systemctl status pisound-btn` | `Active: active (running)` |
| Test Button GPIO Pin State | `gpioget 0 17` | `1` (unpressed), `0` (pressed) |
| Monitor JACK XRUNs | `journalctl -u jack2 -f` | Continuous stream with zero "xrun" warnings |

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

