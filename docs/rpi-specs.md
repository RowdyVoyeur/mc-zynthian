# Hardware Architecture, Raspberry Pi 4 Specifications & Enclosure Manual

Comprehensive hardware specification, component bill of materials (BOM), mechanical assembly guide, and thermal/performance bottleneck analysis for the **`mc-zynthian` Standalone Music Performance Hub** (Stage 1 Core Build).

This document serves as the foundational hardware engineering authority for the [`mc-zynthian`](../README.md) project, detailing the **Raspberry Pi 4 Model B (4GB)**, **Blokas Pisound I2S soundcard**, **Waveshare 5-inch HDMI capacitive touchscreen**, **SayoDevice 12-key macro keyboard**, and custom **3D printed enclosure** ([`assets/case-assembly.stl`](../assets/case-assembly.stl)).

---

## 1. System Vision & Hardware Architecture Overview

The core vision of `mc-zynthian` is to construct an autonomous, road-ready, ultra-low-latency electronic music performance instrument. Unlike standard desktop audio workstations or fragile bare-board setups, Stage 1 unifies compute, studio-grade analog audio conversion, tactile navigation controls, visual feedback, and power distribution into a single rigid chassis.

```mermaid
flowchart TD
    subgraph Enclosure["DIY Custom 3D Enclosure (assets/case-assembly.stl)"]
        subgraph PowerDelivery["Power System"]
            USBC_IN["5.1V / 3.0A USB-C DC Input"]
        end

        subgraph ComputeAudio["Core Processing & Audio Engine"]
            RPi4["Raspberry Pi 4 Model B (4GB RAM)\nBroadcom BCM2711 Quad-Core A72 @ 1.5 GHz"]
            Pisound["Blokas Pisound HAT\n(PCM5102A DAC / PCM1804 ADC / Dual Low-Jitter XOs)"]
        end

        subgraph VisualControl["Interaction & Control Interfaces"]
            Screen["Waveshare 5-inch HDMI LCD (H)\n(800x480 IPS / Capacitive Touch)"]
            Keypad["SayoDevice Macro Keyboard\n(12-Key Mechanical / 9-Key Retro Layout)"]
        end

        USBC_IN -->|5.1V Rail| RPi4
        RPi4 -->|40-Pin GPIO Header\nI2S Audio + SPI MIDI + 5V/3.3V| Pisound
        RPi4 -->|Micro-HDMI to HDMI| Screen
        RPi4 -->|USB 2.0 Port A| Screen
        RPi4 -->|USB 2.0 Port B| Keypad
    end

    subgraph ExternalIO["Stage 1 Physical External I/O"]
        AudioIn["1/4\" Stereo Audio IN (0 to +40 dB)"]
        AudioOut["1/4\" Stereo Audio OUT (Analog Pot)"]
        MidiIn["5-Pin DIN MIDI IN"]
        MidiOut["5-Pin DIN MIDI OUT"]
        Btn["The Button (GPIO 17 Context Push)"]
        USB3_Ext["2x USB 3.0 Ports Available\n(For MC-101 / Push 1 / Storage)"]
        Eth_Ext["Gigabit Ethernet (Stage / Network)"]
    end

    Pisound <--> AudioIn
    Pisound <--> AudioOut
    Pisound <--> MidiIn
    Pisound <--> MidiOut
    Pisound <--> Btn
    RPi4 <--> USB3_Ext
    RPi4 <--> Eth_Ext
```

### 1.1 Core Hardware Interconnect Topology

| Component | Physical Interface | Protocol / Signaling | Primary Function in `mc-zynthian` | Reference Guide |
|---|---|---|---|---|
| **Raspberry Pi 4B (4GB)** | System Host / Motherboard | PCIe, I2S, SPI, USB, HDMI | Core Linux/Zynthian DSP host, synthesis engine, JACK audio server | *This Document* & [`docs/zynthian-guide.md`](zynthian-guide.md) |
| **Blokas Pisound** | 40-Pin GPIO Header | I2S Master Audio + SPI MIDI | High-fidelity $24\text{-bit}/192\text{ kHz}$ DAC/ADC, 5-pin DIN MIDI, The Button | [`docs/pisound-guide.md`](pisound-guide.md) |
| **Waveshare 5" LCD (H)** | Micro-HDMI + USB-A | HDMI Video ($800 \times 480$) + USB HID Multi-Touch | Native pixel-perfect Zynthian GUI visual feedback & auxiliary touch | *This Document* |
| **SayoDevice Keypad** | Internal USB-A | USB HID Keyboard (EEPROM profile) | Primary blind navigation (D-pad, Action A/B, Select, Start, Shift) | [`docs/macrokeyboard-guide.md`](macrokeyboard-guide.md) |
| **Custom 3D Case** | Mechanical Chassis | Rigid PETG/ABS Enclosure | Houses and protects all internal boards, provides port breakouts | [`assets/case-assembly.stl`](../assets/case-assembly.stl) |
| **Teensy 4.1 (Stage 3)** | USB Type-A | USB MIDI & Audio (Class Compliant) | Co-processor / headless synth / DSP voice | [`docs/teensy-guide.md`](teensy-guide.md) |

---

## 2. Raspberry Pi 4 Model B (4GB) Technical Specifications

The computing engine powering the entire ecosystem is the **Raspberry Pi 4 Model B (4GB RAM edition)**.

- **Official Product Documentation:** [raspberrypi.com/products/raspberry-pi-4-model-b/](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)

```
+---------------------------------------------------------------------------------+
|                               RASPBERRY PI 4 MODEL B                            |
|                                                                                 |
|  [Power USB-C]    [Micro-HDMI 0]   [Micro-HDMI 1]    [3.5mm A/V]                |
|       |                 |                |                 |                    |
|  +----+----+       +----+----+      +----+----+       +----+----+   +--------+  |
|  | BCM54213|       |  DDC/CEC|      |  DDC/CEC|       | Stereo/ |   |  DSI   |  |
|  | Gigabit |       | Video 1 |      | Video 2 |       | Video   |   | Display|  |
|  +----+----+       +----+----+      +----+----+       +----+----+   +----+---+  |
|       |                                                                  |      |
|       +----------------------------+-------------------------------------+      |
|                                    |                                            |
|   +--------------------------------+----------------------------------------+   |
|   |                  BROADCOM BCM2711 QUAD-CORE SoC                         |   |
|   |         (4x ARM Cortex-A72 @ 1.5 GHz / 48KB L1I + 32KB L1D / 1MB L2)    |   |
|   |         VideoCore VI 3D GPU @ 500 MHz (OpenGL ES 3.1 / Vulkan 1.2)      |   |
|   +--------------------------------+----------------------------------------+   |
|                                    |                                            |
|         +--------------------------+--------------------------+                 |
|         |                                                     |                 |
|   +-----+------+                                        +-----+------+          |
|   | 4GB LPDDR4 |                                        | PCIe Gen 2 |          |
|   |  SDRAM     |                                        |  (1 Lane)  |          |
|   +------------+                                        +-----+------+          |
|                                                               |                 |
|                                                         +-----+------+          |
|                                                         |  VIA VL805 |          |
|                                                         | USB Host   |          |
|                                                         +-----+------+          |
|                                                               |                 |
|                     +--------------------+--------------------+                 |
|                     |                    |                    |                 |
|                [USB 2.0 Top]       [USB 3.0 Top]        [Ethernet]              |
|                [USB 2.0 Btm]       [USB 3.0 Btm]        [RJ-45 GbE]             |
+---------------------------------------------------------------------------------+
```

### 2.1 Processor Architecture & Microarchitectural Details
- **SoC (System-on-Chip):** Broadcom **BCM2711**, manufactured on a $28\text{ nm}$ CMOS process node.
- **CPU Cores:** Quad-core ARM **Cortex-A72 (ARMv8-A 64-bit)** superscalar processor.
- **Clock Frequency:** Nominal baseline at $1.5\text{ GHz}$ (can safely achieve $1.8\text{ GHz}$ with active cooling).
- **Instruction Pipeline:** Out-of-order execution, speculative execution pipeline with branch prediction, 3-way decode superscalar execution.
- **Internal Cache Hierarchy:**
  - **L1 Cache:** $48\text{ KB}$ instruction cache and $32\text{ KB}$ data cache per physical core.
  - **L2 Cache:** $1\text{ MB}$ unified shared cache among all 4 cores.
- **Floating-Point & Vector Processing:** Dedicated ARM **NEON Advanced SIMD** engine and cryptographic hardware accelerator per core, providing hardware acceleration for real-time DSP filter arithmetic, FFTs, and audio buffer summing.

### 2.2 Memory Subsystem
- **RAM Capacity:** **$4\text{ GB}$ LPDDR4-3200 SDRAM**.
- **Bus Width:** 32-bit dual-channel memory interface ($2 \times 16\text{-bit}$).
- **Peak Bandwidth:** Approximately $4.4\text{ GB/s}$ sustained memory transfer.
- **Why 4GB is the Ideal Sweet Spot for Zynthian:**
  - Stage 1 Zynthian OS base services, Linux kernel, and X11/UI consume approximately $450\text{ MB} - 650\text{ MB}$.
  - The remaining $\approx 3.3\text{ GB}$ of RAM provides abundant unconstrained headroom for caching gigabyte-scale soundfonts (SoundFont2 / SFZ / GigaSampler formats), multiple Fluidsynth instances, high-memory Pianoteq models, and MOD-UI pedalboards without invoking swap files or causing memory fragmentation.

### 2.3 Audio & Peripheral I/O Buses
- **I2S / PCM Digital Audio Header:**
  - Pins on the 40-pin GPIO header: GPIO 18 (PCM CLK), GPIO 19 (PCM Frame Sync / LRCLK), GPIO 20 (PCM Data IN), GPIO 21 (PCM Data OUT).
  - Operates in **I2S Slave Mode** relative to the Blokas Pisound soundcard. The Pisound board drives the clock lines with dedicated ultra-low-jitter quartz oscillators, bypassing the Pi's internal fractional PLL.
- **SPI Hardware Bus:**
  - GPIO 10 (MOSI), GPIO 9 (MISO), GPIO 11 (SCLK), GPIO 8 (CE0).
  - Leveraged by Pisound's high-speed SPI-to-UART microcontroller for rock-solid, jitter-free 5-pin DIN MIDI transmission and reception.
- **The Button Input Line:**
  - GPIO 17 (Pin 11) is configured as an active-low interrupt line directly tied to Pisound's physical tactile button.

### 2.4 USB Host Controller Architecture
- **Host Controller:** **VIA VL805** 4-port SuperSpeed USB 3.0 Host Controller.
- **Bus Uplink:** Connected to the BCM2711 SoC via a single **PCI Express (PCIe) Gen 2 x1 lane**, providing theoretical raw bandwidth of $5.0\text{ Gbps}$ ($\approx 4\text{ Gbps}$ practical throughput after 8b/10b encoding).
- **Physical Ports & Internal Bus Topology:**
  - **$2 \times$ USB 3.0 Type-A (Blue connectors):** Routed to the VL805's SuperSpeed controller ($5\text{ Gbps}$) and its internal USB 2.0 hub.
  - **$2 \times$ USB 2.0 Type-A (Black connectors):** Routed exclusively to the internal USB 2.0 hub.
  - **Single Shared USB 2.0 Bus:** Crucially, the USB 2.0 data lines of **all 4 physical ports** connect through a single internal VIA Labs USB 2.0 hub (USB ID `2109:3431`). Therefore, **all USB 2.0 and USB 1.1 peripherals (Roland MC-101, Ableton Push 1, Korg nanoKONTROL, SayoDevice, Waveshare touch controller, and Teensy 4.1) share a single $480\text{ Mbps}$ bus regardless of whether they are plugged into blue or black ports**.
  - The blue USB 3.0 ports only provide dedicated $5\text{ Gbps}$ bandwidth to genuine SuperSpeed USB 3.0 devices (such as an external USB 3.0 NVMe/SATA SSD).
  - The shared $480\text{ Mbps}$ USB 2.0 bandwidth is still far more than adequate for streaming 10 channels of audio at $44.1\text{ kHz}$ along with MIDI and HID data (which takes $< 25\text{ Mbps}$).
- **Power Distribution & 1.2A Hardware Limit:**
  - On the Raspberry Pi 4, the hardware automatically provides a combined maximum of **$1.2\text{ A}$ total** across all 4 USB ports.
  - Note: `max_usb_current=1` is a legacy Raspberry Pi 2/3 setting that has **no effect on the Pi 4** (the power switch chip AP2553 on Pi 4 hardwires this limit without needing software flags).

---

## 3. Waveshare 5-Inch HDMI LCD (H) Touchscreen Specifications

The primary visual interaction display for `mc-zynthian` is the **Waveshare 5-inch HDMI LCD (H)** with capacitive USB multi-touch.

- **Official Product Documentation:** [waveshare.com/5inch-hdmi-lcd-h.htm](https://www.waveshare.com/5inch-hdmi-lcd-h.htm)

```
+---------------------------------------------------------------------------------+
|                       WAVESHARE 5-INCH HDMI LCD (H)                             |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                                                                         |   |
|   |                                                                         |   |
|   |                      800 x 480 IPS DISPLAY PANEL                        |   |
|   |                         (Active Area: 5.0")                             |   |
|   |                       5:3 Aspect Ratio / 187 PPI                        |   |
|   |                                                                         |   |
|   |                                                                         |   |
|   +-------------------------------------------------------------------------+   |
|                                                                                 |
|   [HDMI Full-Size Input]   [USB Touch / 5V Power]   [Backlight Switch / Slider] |
+---------------------------------------------------------------------------------+
```

### 3.1 Display Panel Technical Parameters
- **Diagonal Screen Size:** $5.0\text{ inches}$ ($127\text{ mm}$).
- **Hardware Native Resolution:** **$800 \times 480\text{ pixels}$** (WVGA, 5:3 aspect ratio).
- **Pixel Density:** $\approx 187\text{ PPI}$ (Pixels Per Inch).
- **Panel Technology:** **IPS (In-Plane Switching)** wide-gamut LCD panel.
- **Viewing Angles:** $178^\circ$ horizontal and $178^\circ$ vertical viewing cone, guaranteeing crystal-clear visibility without chromatic inversion when viewed from off-axis angles on stage or desktop stands.
- **Backlight Control:** Independent hardware switch / potentiometer for dimming or switching off the LED backlight to conserve battery or USB current.

### 3.2 Capacitive Touch Subsystem
- **Touch Sensing Type:** Projected Capacitive Touch (PCAP).
- **Multi-Touch Support:** Up to 5 concurrent touch points.
- **Surface Material:** Toughened optical glass overlay ($6\text{H}$ surface hardness) with scratch-resistant coating.
- **Host Interface:** Standard USB HID Multi-Touch protocol.
- **Driver Compatibility:** Fully plug-and-play under Linux kernel `hid-multitouch` driver (zero binary blobs or proprietary modules required).

### 3.3 Display Configuration Under Modern KMS / ZynthianOS

Modern Zynthian builds (ZynthianOS Oram and Vangelis, built on 64-bit Debian Bookworm and Trixie) use the Linux kernel standard **KMS (Kernel Mode Setting)** graphics driver via `dtoverlay=vc4-kms-v3d`.

> [!NOTE]
> **KMS vs Legacy `config.txt` Directives:**
> Under the modern KMS driver, legacy video timing parameters such as `hdmi_group`, `hdmi_mode`, `hdmi_cvt`, and `hdmi_drive` in `/boot/firmware/config.txt` are **completely ignored** by the Linux DRM subsystem.
>
> 1. **Plug-and-Play EDID:** In almost all cases, the Waveshare 5-inch HDMI LCD (H) provides standard EDID over the HDMI DDC line, and the KMS driver automatically detects and negotiates native $800 \times 480$ at $60\text{ Hz}$.
> 2. **Configuring via Zynthian Webconf:** Navigate to **Hardware -> Display** in the Zynthian Webconf interface and select **Generic HDMI Display** with resolution set to **$800 \times 480$**.
> 3. **Manual Timing Override (cmdline.txt):** If the display fails to auto-negotiate, append the video mode directly to the single kernel command line in `/boot/firmware/cmdline.txt`:
>    ```text
>    video=HDMI-A-1:800x480M@60
>    ```
> 4. **Inspection & Verification:** You can verify the active KMS video mode and timings from the terminal with:
>    ```bash
>    cat /sys/class/drm/card*-HDMI-A-1/modes
>    ```

### 3.4 Operational Benefits & Physical Limitations in Zynthian

#### 1:1 Native Resolution Synergy
Historically, the official Zynthian UI was designed and geometrically proportioned for an $800 \times 480$ screen (the resolution of the official Raspberry Pi 7-inch DSI touchscreen). Because this 5-inch Waveshare LCD possesses identical $800 \times 480$ pixel geometry:
- **Zero Pixel Distortion:** Every UI element, rotary knob graphic, meter bar, and font glyph maps 1:1 to physical pixels without bilinear filtering blur or non-integer scaling artifacts.
- **Minimal GPU Composition Overhead:** The VideoCore VI GPU renders the framebuffer with zero scaling penalty, leaving memory bandwidth entirely available for real-time audio threads.

#### Physical Touch Target Trade-Offs
While pixel-perfect, compressing an $800 \times 480$ layout onto a $5.0\text{-inch}$ diagonal ($187\text{ PPI}$) means that UI buttons and rotary touch rings measure only $6\text{ mm} - 9\text{ mm}$ on the glass:
- In a live performance environment with stage vibrations or rapid playing, tapping small touch controls can lead to mis-clicks.
- **Architectural Solution:** This physical constraint is the explicit reason **Stage 1 integrates the SayoDevice 12-key macro keyboard** ([`docs/macrokeyboard-guide.md`](macrokeyboard-guide.md)). Musician navigation (Up, Down, Left, Right, Enter/A, Back/B, Screen/Select, Transport/Start) is handled $100\%$ by tactile mechanical switches, freeing the touchscreen to serve as a visual status monitor and secondary assist.

---

## 4. Custom 3D Printed Enclosure & Mechanical Assembly

To eliminate stage clutter and fragile ribbon cables, the entire system is encased in a custom-designed, 3D-printable unibody chassis.

- **3D CAD Assembly Model:** [`assets/case-assembly.stl`](../assets/case-assembly.stl)

```
+---------------------------------------------------------------------------------+
|                       CASE ASSEMBLY ENVELOPE (PERSPECTIVE)                      |
|                                                                                 |
|                   +---------------------------------------+                     |
|                  /                                       /|                     |
|                 /       [WAVESHARE 5" LCD BEZEL]        / |                     |
|                /         (Angled 25° for Stage)        /  |                     |
|               +---------------------------------------+   |                     |
|               |                                       |   | Height:             |
|               |  [SAYODEVICE 9-KEY RETRO CONTROLLER]  |   | 130.95 mm           |
|               |   [O] UP       [Fn] [A] [B]           |   |                     |
|               |  [O][O][O]     [SEL] [START]          |   |                     |
|               +---------------------------------------+   |                     |
|               |  [PISOUND 1/4" AUDIO & DIN MIDI I/O]  |   /                     |
|               |  (In Gain, Vol, In/Out Jacks, MIDI)   |  / Depth:               |
|               +---------------------------------------+ /  282.00 mm            |
|               | [RPi 4 USB-C / USB 3.0 / GbE PORTS]   |/                        |
|               +---------------------------------------+                         |
|               <------------- Width: 152.00 mm -------->                         |
+---------------------------------------------------------------------------------+
```

### 4.1 Measured Bounding Box Dimensions
Analysis of the 3D mesh in [`assets/case-assembly.stl`](../assets/case-assembly.stl) confirms the exact physical build envelope:

| Axis | Dimension ($mm$) | Coordinate Extents ($mm$) | Description |
|---|---|---|---|
| **Width ($X$)** | **$152.00\text{ mm}$** | $-41.00\text{ mm}$ to $+111.00\text{ mm}$ | Lateral width accommodating Pisound 1/4" jacks & Pi 4 layout |
| **Depth ($Y$)** | **$282.00\text{ mm}$** | $-72.00\text{ mm}$ to $+210.00\text{ mm}$ | Longitudinal footprint housing screen, keyboard, and soundcard |
| **Height ($Z$)** | **$130.95\text{ mm}$** | $-70.11\text{ mm}$ to $+60.84\text{ mm}$ | Ergonomic wedge profile providing $25^\circ$ tilted viewing angle |
| **Mesh Density** | **$466,532\text{ facets}$** | Binary STL format | High-precision fillets, screw bosses, and connector cutouts |

### 4.2 Chassis Geometry & Assembly Guidance

The physical enclosure design integrates the entire computing, display, audio, and keyboard stack into a single unified chassis:

1. **Physical Measurements (from `assets/case-assembly.stl`):**
   - The enclosure bounding box is **$152.00\text{ mm (Width)} \times 282.00\text{ mm (Depth)} \times 130.95\text{ mm (Height)}$** (466,532 facets).
   - The upper face provides an angled deck for the Waveshare 5-inch display.
   - The lower front deck houses the SayoDevice macro keyboard, where the faceplate physically masks/hides Keys 1, 3, and 10 to present a 9-key retro controller layout ([`docs/macrokeyboard-guide.md`](macrokeyboard-guide.md)).
   - Side and rear cutouts provide access to Pisound's 1/4" audio jacks, 5-pin DIN MIDI ports, gain/volume pots, The Button, and the Pi 4's Ethernet, USB, and USB-C power ports.

2. **Builder Recommendations (To Be Confirmed Against Physical Prints):**
   - **Internal Standoffs & Fasteners:** Typical assembly utilizes M2.5 threaded brass heat-set inserts on the base floor, with standard M2.5 standoffs ($\approx 11\text{ mm} - 12\text{ mm}$) to secure the Raspberry Pi and Pisound stack. Confirm exact standoff heights against your printed part tolerances.
   - **Internal Interconnects:** Short low-profile micro-HDMI to HDMI cables (or ribbon bridges) and short right-angle USB jumper cables route internally to the screen and SayoDevice.
   - **External Ports:** The Pi 4's remaining USB ports and Gigabit Ethernet port remain accessible from the rear for external gear (Roland MC-101, Ableton Push 1, Korg nanoKONTROL, or storage).

### 4.3 Recommended 3D Printing Specifications

> [!IMPORTANT]
> **Filament Material Selection:**
> The Broadcom BCM2711 SoC dissipates significant heat ($5\text{W} - 7.5\text{W}$) inside an enclosed space. Standard PLA has a glass transition temperature ($T_g$) of only $\approx 55^\circ\text{C} - 60^\circ\text{C}$ and will warp or deform over long performance sessions under high DSP load. **PETG or ABS/ASA is strongly recommended**.

| Parameter | Recommended Setting | Rationale |
|---|---|---|
| **Material** | **PETG** or **ABS / ASA** | $T_g \ge 75^\circ\text{C}$ to $105^\circ\text{C}$; impervious to internal heatsink thermal radiation |
| **Print Bed Size** | Minimum $300 \times 300\text{ mm}$ | Case depth is $282\text{ mm}$; can be oriented diagonally on $300\text{ mm}$ beds |
| **Layer Height** | $0.20\text{ mm}$ ($0.28\text{ mm}$ draft) | Balances print speed with structural layer adhesion and aesthetic finish |
| **Infill Density** | $25\% - 30\%$ | Ensures structural rigidity when plugging/unplugging 1/4" audio jacks |
| **Infill Pattern** | **Gyroid** | Isotropic strength in all three physical dimensions |
| **Perimeter Walls** | 4 perimeters ($1.6\text{ mm}$ thickness) | Solid anchoring for M2.5/M3 brass threaded heat-set inserts |
| **Top / Bottom Layers** | 5 top, 4 bottom | Prevents top surface sagging over wide internal cable voids |
| **Print Orientation** | Base flat on build plate | Minimizes internal support requirements; creates smooth top bezels |

---

## 5. Bill of Materials (BOM) & Estimated Build Costs

The following table provides an exhaustive breakdown of all components, hardware fasteners, cables, and raw materials required to assemble the complete Stage 1 `mc-zynthian` hardware unit.

### 5.1 Component Breakdown Table

| Item # | Component Name | Exact Model / Spec | Primary Role | Sourcing Reference | Est. Cost (USD) | Est. Cost (EUR) |
|---|---|---|---|---|---|---|
| **1** | **Single Board Computer** | Raspberry Pi 4 Model B (4GB RAM) | Core DSP Host & Sound Engine | [Raspberry Pi](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) | \$55 – \$65 | €55 – €65 |
| **2** | **Audio & MIDI HAT** | Blokas Pisound Soundcard & MIDI | $24\text{b}/192\text{k}$ Audio, DIN MIDI, The Button | [Blokas Labs](https://blokas.io/pisound/) | \$105 – \$115 | €99 – €109 |
| **3** | **Display & Touch** | Waveshare 5-inch HDMI LCD (H) | $800 \times 480$ IPS LCD + USB PCAP Touch | [Waveshare](https://www.waveshare.com/5inch-hdmi-lcd-h.htm) | \$42 – \$50 | €40 – €48 |
| **4** | **Tactile Macro Controller** | SayoDevice 12-Key Mechanical Keypad | 9-Key Retro D-Pad Navigation | [SayoDevice](https://sayodevice.com/) | \$18 – \$24 | €16 – €22 |
| **5** | **Storage Media** | MicroSDXC 64GB (A2 / V30 / U3) | Zynthian OS, Soundfonts & Presets | SanDisk Extreme / Samsung EVO | \$12 – \$16 | €11 – €15 |
| **6** | **Power Supply** | Official Raspberry Pi 15.3W USB-C | Clean 5.1V / 3.0A DC Power Delivery | Official RPi Supply | \$8 – \$12 | €8 – €12 |
| **7** | **Display Ribbon Cable** | Micro-HDMI to Full HDMI Flat Ribbon | Internal video connection (RPi to LCD) | Low-profile angled ribbon (15cm) | \$6 – \$9 | €5 – €8 |
| **8** | **USB Interconnects** | Short Right-Angle USB Jumpers | Internal touch & keypad data routing | USB-A to Type-C / Micro-USB (2x) | \$5 – \$8 | €4 – €7 |
| **9** | **Fasteners & Inserts** | M2.5 & M3 Brass Heat-Set Inserts + Screws | Motherboard & screen standoff mounting | Metric hardware kit | \$6 – \$10 | €5 – €9 |
| **10** | **3D Printing Material** | PETG / ABS Filament ($\approx 400\text{g}$) | Printing [`assets/case-assembly.stl`](../assets/case-assembly.stl) | Standard 1kg spool (fractional) | \$10 – \$14 | €9 – €13 |
| **11** | **Active Thermal Cooling** | Low-Noise 5V / 3.3V 30mm Fan + Heatsinks | Sustained 1.5–1.8 GHz operation without throttling | Noctua NF-A4x10 5V or Pi fan kit | \$6 – \$15 | €6 – €14 |
| **TOTAL** | **Complete Hardware Build** | **Stage 1 Autonomous Instrument** | **Fully Functional Standalone Zynthian** | — | **\$273 – \$338** | **€258 – €322** |

> [!TIP]
> **Component Sourcing Alternatives:**
> - If an 8GB Raspberry Pi 4 is already available, it is $100\%$ drop-in compatible. The extra 4GB of RAM is primarily beneficial when loading massive, multi-gigabyte piano soundfont libraries or running background web servers.
> - A standard MicroSD card reader can be supplemented by configuring the Raspberry Pi 4 to boot directly from a high-speed USB 3.0 SSD (M.2 NVMe in a low-profile USB enclosure) for instantaneous preset switching and virtually unlimited soundfont storage.

---

## 6. Hardware Performance Bottlenecks & Thermal Engineering

Audio DSP synthesis is one of the most demanding real-time computing tasks a microcontroller or SoC can execute. In standard desktop computing, a $5\text{ ms}$ CPU stall or background task switch is invisible. In real-time audio running at $48\text{ kHz}$ with a $64\text{-sample}$ buffer, the entire audio synthesis block must execute in under:

$$T_\text{deadline} = \frac{\text{Frames}}{\text{Sample Rate}} = \frac{64}{48000\text{ Hz}} \approx 1.333\text{ ms}$$

Missing this execution deadline even once causes an **XRUN** (buffer underrun), resulting in audible pops, clicks, or momentary dropouts in the PA system. Understanding hardware bottlenecks is essential for bulletproof performance.

```mermaid
flowchart TD
    subgraph Bottlenecks["Critical Hardware Performance Vectors"]
        Thermal["Thermal Envelope & Throttling\n(BCM2711 @ 80°C clamps clock to 1.0 GHz)"]
        USB["USB Isochronous Scheduling\n(VL805 PCIe Bus & Endpoint Saturation)"]
        Power["Power Supply Voltage Drops\n(Under-voltage < 4.65V clamps CPU turbo)"]
        Memory["Storage & Soundfont IOPS\n(MicroSD Random Read Stalls on Patch Load)"]
    end

    Thermal -->|Trigger: High Ambient / Enclosed Box| XRUN["JACK Audio XRUNs\n(Audio Dropouts / Pops / Clicks)"]
    USB -->|Trigger: High Channel Count (MC-101 10-Out)| XRUN
    Power -->|Trigger: Substandard 5V 2A Phone Charger| XRUN
    Memory -->|Trigger: Slow MicroSD Random Reads| XRUN
```

### 6.1 Thermal Envelope & Throttling Dynamics

The Broadcom BCM2711 SoC dissipates between $3.5\text{W}$ at idle and up to $7.5\text{W}$ under full multi-core polyphonic DSP synthesis (e.g., ZynAddSubFX + Pianoteq running concurrently).

Inside a sealed 3D-printed enclosure without ventilation or active air movement:
1. **$80^\circ\text{C}$ Threshold (Soft Throttle):** When the junction temperature reaches $80^\circ\text{C}$, the Raspberry Pi 4 firmware initiates thermal management, capping maximum clock boosts and stepping down GPU/CPU boost clocks.
2. **$85^\circ\text{C}$ Threshold (Hard Throttle):** If the internal junction temperature reaches $85^\circ\text{C}$, the hardware thermal governor **instantly drops the CPU clock frequency from $1500\text{ MHz}$ down to $1000\text{ MHz}$ or lower**.
3. **The XRUN Cascade:** When CPU clock speed drops mid-performance, the real-time audio thread instantly misses its processing deadline ($1.33\text{ ms}$ at 64 samples / 48 kHz). The JACK audio server reports consecutive XRUNs, resulting in audio pops or dropouts.

#### Engineering Mitigations:
- **Heatsinks:** Affix high-thermal-conductivity aluminum or copper heatsinks directly to the BCM2711 SoC, the RAM package, and the VL805 USB controller using high-quality thermal tape or paste.
- **Cooling Fan (Optional):** In enclosed cases under sustained heavy load or high ambient temperatures, a small low-noise $30\text{ mm}$ fan wired to the 3.3V GPIO rail (Pin 1) provides quiet convective airflow across the heatsinks.
- **Ventilation Geometry in Chassis:** Ensure the 3D-printed chassis features convective intake louvers along the bottom floor and exhaust slots along the upper rear wall.

### 6.2 USB Bus Topology & Bandwidth Distribution

The Raspberry Pi 4 utilizes a **VIA VL805** PCIe-to-USB 3.0 controller connected to the SoC via a single PCIe Gen 2 x1 lane.

As described in Section 2.4, the USB 2.0 lines of **all four physical ports** share a single internal VIA Labs USB 2.0 hub (ID `2109:3431`). Therefore:
- The **Roland MC-101**, **Ableton Push 1**, **Korg nanoKONTROL**, **SayoDevice keypad**, **Waveshare touchscreen**, and **Teensy 4.1** all operate on the same shared $480\text{ Mbps}$ USB 2.0 bus, regardless of whether they are plugged into the blue or black ports.
- **Bandwidth Reality:** Isochronous audio from the MC-101 streaming 10 channels out and 4 channels in at $24\text{-bit}/44.1\text{ kHz}$ consumes $\approx 10.6\text{ Mbps}$ of payload bandwidth—less than $3\%$ of the $480\text{ Mbps}$ USB 2.0 bus capacity. Bandwidth saturation is not the bottleneck.
- **The True Bottleneck:** The real constraints are **USB interrupt polling schedules** and **USB downstream power budget**. Keep cables short and high-quality, and manage device power carefully as detailed below.

### 6.3 Power Delivery, Voltage Sag & Downstream USB Budget

Under full load, current consumption across the internal Stage 1 hardware stack is substantial:
- **Raspberry Pi 4B (4 Cores DSP):** $\approx 900\text{ mA} - 1200\text{ mA}$
- **Waveshare 5" LCD (Backlight Active + Touch):** $\approx 400\text{ mA} - 500\text{ mA}$
- **Blokas Pisound (ADC, DAC, Op-Amps, Oscillators):** $\approx 180\text{ mA} - 220\text{ mA}$
- **SayoDevice Keypad (Mechanical Switches + RGB LEDs):** $\approx 100\text{ mA} - 200\text{ mA}$
- **Total Combined Peak Current Draw (Internal):** **$\approx 2.12\text{ A}$ to $2.60\text{ A}$ at $5.1\text{V}$**

#### Downstream USB Current Budget (1.2A Total)
The Raspberry Pi 4 hardware enforces a combined maximum limit of **$1.2\text{ A}$** across all four downstream USB ports:
- **Internal Stage 1 Baseline:** The Waveshare LCD USB touch/power ($\approx 400\text{ mA} - 500\text{ mA}$) and SayoDevice keypad ($\approx 100\text{ mA} - 150\text{ mA}$) draw $\approx 500\text{ mA} - 650\text{ mA}$ combined, leaving $\approx 550\text{ mA} - 700\text{ mA}$ of headroom.
- **Ableton Push 1 Bus-Power Behavior:** The Ableton Push 1 is fully class-compliant and **can operate entirely on USB bus power alone** without any wall adapter (its internal firmware automatically dims the pads and LCD to $\approx 30\%$ brightness). When bus-powered, Push 1 draws up to $500\text{ mA}$.
- **Managing Multiple External Controllers (Stages 2 & 3):**
  If Push 1 (bus-powered, $500\text{ mA}$), MC-101 (bus-powered, $500\text{ mA}$), nanoKONTROL ($100\text{ mA}$), and Teensy 4.1 ($100\text{ mA}$) are all plugged simultaneously into the Pi's USB ports without external power, the combined downstream draw ($\approx 1.8\text{ A}$) will exceed the Pi's $1.2\text{ A}$ hardware limit, causing USB disconnects or triggering under-voltage CPU throttling.

#### Recommended Power Strategies for Multi-Device Setups:
1. **Ableton Push 1:** Operates cleanly on USB bus power alone when used with the internal screen and keypad. If multiple additional USB devices are plugged directly into the Pi, connecting Push 1's optional $12\text{V DC}$ power supply eliminates its backlight current draw from the Pi's USB bus (and restores full $100\%$ pad brightness).
2. **Roland MC-101:** Run on 4x AA batteries (holding the `[VALUE]` button while powering on forces battery operation even with USB connected) to draw $0\text{ mA}$ from the Pi's USB bus.
3. **Powered USB Hub:** Connecting external controllers (Push 1, MC-101, nanoKONTROL, Teensy) through an external powered USB hub completely bypasses the Pi's $1.2\text{ A}$ downstream limit and guarantees clean, sag-free power.

#### The Under-Voltage Danger & Host Power
Standard USB phone chargers or generic micro-USB cables with high internal resistance suffer severe voltage drops under a $2.5\text{A}$ load. If the voltage at the Pi's PMIC drops below **$4.65\text{V}$**:
- The Pi's onboard power supervisor asserts an **under-voltage alarm** (historically represented by the yellow lightning bolt icon).
- The Linux kernel instantly throttles the CPU clock frequency down to reduce power draw, triggering massive audio XRUNs.
- **Rule:** Always power the system with the **official Raspberry Pi 15.3W USB-C power supply (5.1V / 3.0A)** or a verified industrial buck converter capable of providing a steady $5.1\text{V} - 5.2\text{V}$ under dynamic load.

#### Audio Ground Loops & Isolation
Because the Raspberry Pi, Pisound, Roland MC-101, and external studio monitors or mixers often share a common electrical ground via USB and audio shield conductors, ground loop hum (a low $50\text{Hz}/60\text{Hz}$ mains hum accompanied by high-frequency digital hash from USB bus transactions) can infiltrate high-gain audio inputs.
- Use balanced audio interconnects or an inline ground-loop audio isolator (DI box with ground lift) when connecting Pisound's 1/4" outputs to house PA systems.

---

## 7. System Diagnostics & Health Verification

To inspect, monitor, and diagnose the physical health of the Raspberry Pi hardware under actual live performance conditions, execute the following commands via SSH or terminal:

### 7.1 Real-Time Thermal & Throttling Status

```bash
# Check instantaneous CPU core temperature
vcgencmd measure_temp

# Check current CPU operating frequency in Hz
vcgencmd measure_clock arm

# Check core SoC supply voltage
vcgencmd measure_volts core
```

### 7.2 Decoding the Throttling Bitmask (`vcgencmd get_throttled`)

The `vcgencmd get_throttled` command returns a hexadecimal bitmask reporting hardware-level under-voltage, frequency capping, and thermal throttling events:

```bash
vcgencmd get_throttled
# Example clean output: throttled=0x0
# Example problematic output: throttled=0x50005
```

#### Bitmask Breakdown Reference Table:
| Bit | Hex Value | Meaning / Severity |
|---|---|---|
| **0** | `0x00001` | **Under-voltage detected right now!** (PSU is dropping below $4.65\text{V}$) |
| **1** | `0x00002` | **ARM frequency capped right now!** (CPU throttled due to power/thermal) |
| **2** | `0x00004` | **Currently throttled!** (Active thermal throttling in progress) |
| **3** | `0x00008` | **Soft temperature limit active right now!** ($> 80^\circ\text{C}$) |
| **16**| `0x10000` | Under-voltage has occurred since last boot (historical warning) |
| **17**| `0x20000` | ARM frequency capping has occurred since last boot |
| **18**| `0x40000` | Throttling has occurred since last boot |
| **19**| `0x80000` | Soft temperature limit has occurred since last boot |

> [!CAUTION]
> If `vcgencmd get_throttled` reports **`0x1`** or **`0x50005`**, the system is suffering from under-voltage. Audio stability cannot be guaranteed until the power supply and USB-C cable are upgraded.

### 7.3 USB Topology & Endpoint Inspection

```bash
# Display hierarchical tree view of all connected USB devices and negotiation speeds
lsusb -t

# Check kernel logs for USB disconnects, reset events, or power anomalies
dmesg | grep -i -E "voltage|thermal|throttled|under-voltage|xrun"
```

### 7.4 Real-Time Audio DSP Performance Monitoring

```bash
# Monitor JACK real-time CPU load and XRUN count in real-time
jack_cpu_load
```

---

## 8. Summary & Stage Roadmap Integration

The hardware detailed in this manual provides the rigid, low-noise foundation upon which the rest of the project is constructed:

1. **Stage 1 (Current):** Standalone operations driven entirely by the **Raspberry Pi 4**, **Blokas Pisound**, **Waveshare 5-inch LCD**, and **SayoDevice Macro Keyboard**, enclosed within [`assets/case-assembly.stl`](../assets/case-assembly.stl) and managed by ZynthianOS Vangelis (see [`docs/zynthian-guide.md`](zynthian-guide.md)).
2. **Stage 2:** Expanding external audio/MIDI interconnects by connecting the **Roland MC-101** (10-out/4-in streaming over USB 3.0, see [`docs/mc101-guide.md`](mc101-guide.md) and [`docs/mc101-sysex.md`](mc101-sysex.md)) and the **Korg nanoKONTROL 1** (see [`docs/nanokontrol-guide.md`](nanokontrol-guide.md)).
3. **Stage 3:** Integrating deep physical control via the **Ableton Push 1** (see [`docs/push-guide.md`](push-guide.md) and [`docs/push-protocols.md`](push-protocols.md)) and custom modular voices via a repurposed **Teensy 4.1** (see [`docs/teensy-guide.md`](teensy-guide.md)).

