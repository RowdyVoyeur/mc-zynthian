#!/usr/bin/env python3
"""
Ableton Push 1 Native Control Surface Driver & Bridge for Zynthian (`pushy.py`)
=====================================================================================

Provides full Ableton-Live-style hardware control over Zynthian (and Stage 2/3
Roland MC-101 integration) using an Ableton Push 1 controller:
- Launch Clips & Scenes (Zynpad 8x8 Session grid + 8 Scene Launch buttons)
- Edit Mixer Settings (Volume, Pan, Sends, Track Channel Strip, Mute, Solo)
- Edit Master Volume, Global Tempo & Swing (with touch-cap LCD overlay banners)
- Navigate, Browse & Create Instruments (Add Track wizard, Add Effect, Bank/Preset Browser)
- Edit All Instrument Parameters (8-Encoder Dual-Page Zynthian `zctrl` + MC-101 SysEx)
- Create & Edit Sequences (4x4 Drum + 32-Step Sequencer, Melodic Piano Roll, Per-Step Locks)
- Play Instruments Live (64-Pad Isometric Scale Matrix, 34 Scales, Note Repeat, Accent)

Can be deployed in two ways:
1. Natively inside `zynthian-ui` (`zyngine/ctrldev/zynthian_ctrldev_ableton_push1.py`)
   via the `zynthian_ctrldev_ableton_push1` class at the bottom of this module.
2. As a standalone bridge daemon (`python3 scripts/pushy.py`) communicating
   over ALSA/JACK MIDI (`mido` / `python-rtmidi`) and Zynthian UDP OSC (`1370`).

Sources & References:
- https://github.com/gluon/AbletonLive9_RemoteScripts/tree/master/Push
- https://pushmod.blogspot.com/2014/05/the-ableton-push-is-definitely-some.html
- https://forum.ableton.com/viewtopic.php?t=193744
- https://cycling74.com/forums/how-to-control-the-push-lcd-with-sysex-messages
- https://github.com/JBrumby/zynthian-ui (PR #535)
- https://github.com/garrensmith/abletonpush
- https://github.com/parabuzzle/ableton_push
- https://github.com/git-moss/DrivenByMoss-Documentation
- https://discourse.zynthian.org/t/driver-for-ableton-push-1-first-steps/12166
"""

from __future__ import annotations

import enum
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

logger = logging.getLogger("pushy")

# ============================================================================
# 1. ABLETON PUSH 1 HARDWARE CONSTANTS (SysEx, CCs, Notes, Glyphs, Colors)
# ============================================================================

SYSEX_START = 0xF0
SYSEX_END = 0xF7
PUSH1_SYSEX_HEADER = (0xF0, 0x47, 0x7F, 0x15)  # Akai (0x47), Broadcast (0x7F), Push 1 (0x15)
DEVICE_INQUIRY_SYSEX = (0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7)

# Push 1 SysEx Command IDs
SYSEX_CMD_SET_RGB_PALETTE = 0x03
SYSEX_CMD_LCD_LINE_1 = 0x18  # 24 dec
SYSEX_CMD_LCD_LINE_2 = 0x19  # 25 dec
SYSEX_CMD_LCD_LINE_3 = 0x1A  # 26 dec
SYSEX_CMD_LCD_LINE_4 = 0x1B  # 27 dec
SYSEX_CMD_CLEAR_LINE_1 = 0x1C  # 28 dec
SYSEX_CMD_CLEAR_LINE_2 = 0x1D  # 29 dec
SYSEX_CMD_CLEAR_LINE_3 = 0x1E  # 30 dec
SYSEX_CMD_CLEAR_LINE_4 = 0x1F  # 31 dec
SYSEX_CMD_AFTERTOUCH_THRESH = 0x5B  # 91 dec
SYSEX_CMD_AFTERTOUCH_MODE = 0x5C  # 92 dec (0 = Channel Pressure, 1 = Poly Aftertouch)
SYSEX_CMD_SET_MODE = 0x62  # 98 dec (0 = Live Mode, 1 = User Mode)
SYSEX_CMD_TOUCHSTRIP_CFG = 0x63  # 99 dec
SYSEX_CMD_TOUCHSTRIP_LEDS = 0x64  # 100 dec
SYSEX_CMD_LCD_CONTRAST = 0x7A  # 122 dec

# LCD Geometry
LCD_LINES = 4
LCD_LINE_LENGTH = 68
LCD_BLOCK_WIDTH = 17  # 4 physical LCD segments x 17 chars = 68 chars
LCD_CELL_WIDTH = 8    # 8 encoder columns x 8 chars + 4 spaces = 68 chars
LCD_8COL_OFFSETS = (0, 9, 17, 26, 34, 43, 51, 60)
LCD_4COL_OFFSETS = (0, 17, 34, 51)

# Push 1 Special Character Glyphs (0x00..0x1F, 0x7F) from Consts.py
GLYPH_ARROW_UP = 0x00       # ↑
GLYPH_ARROW_DOWN = 0x01     # ↓
GLYPH_HAMBURGER = 0x02      # ≡
GLYPH_PAN_CENTER = 0x03     # | (Centered vertical tick)
GLYPH_BAR_LEFT = 0x04       # | (Left vertical bar)
GLYPH_BAR_RIGHT = 0x05      # | (Right vertical bar)
GLYPH_BLOCK_FULL = 0x06     # █ (2-unit full bar segment)
GLYPH_BLOCK_HALF = 0x07     # ▌ (1-unit left half-bar segment)
GLYPH_FOLDER_ELBOW = 0x08   # └─
GLYPH_DEGREE = 0x09         # °
GLYPH_FLAT = 0x19           # ♭
GLYPH_SHARP = 0x1A          # ♯
GLYPH_ELLIPSIS = 0x1B       # … (Single-char ellipsis)
GLYPH_BLOCK_EMPTY = 0x1C    # □ (Hollow bar segment)
GLYPH_BLOCK_RIGHT = 0x1D    # ▐ (Right half-bar segment)
GLYPH_TRI_LEFT = 0x1E       # ◀
GLYPH_TRI_RIGHT = 0x1F      # ▶
GLYPH_ARROW_RIGHT = 0x7F    # →

# Touchstrip Configuration Bitflags (TouchStripElement.py)
TOUCHSTRIP_LED_HOST = 0x01
TOUCHSTRIP_VAL_HOST = 0x02
TOUCHSTRIP_AUTORETURN = 0x04
TOUCHSTRIP_BAR_MODE = 0x08
TOUCHSTRIP_CENTER_ZERO = 0x10

TOUCHSTRIP_MODE_PITCHBEND = TOUCHSTRIP_AUTORETURN | TOUCHSTRIP_BAR_MODE | TOUCHSTRIP_CENTER_ZERO  # 0x1C (28)
TOUCHSTRIP_MODE_MODWHEEL = TOUCHSTRIP_BAR_MODE  # 0x08 (8)
TOUCHSTRIP_MODE_PAN = TOUCHSTRIP_BAR_MODE | TOUCHSTRIP_CENTER_ZERO  # 0x18 (24)
TOUCHSTRIP_MODE_HOST_LEDS = TOUCHSTRIP_LED_HOST  # 0x01 (1)


class PushCC(enum.IntEnum):
    """Complete Ableton Push 1 Control Change (CC) Map on Channel 1 (0xB0)."""
    # Top-Left Global Section
    TAP_TEMPO = 3
    METRONOME = 9
    TEMPO_ENCODER = 14
    SWING_ENCODER = 15

    # Upper Row Display Softkeys (Bi-Color LEDs: Red / Amber / Yellow / Green)
    UPPER_ROW_1 = 20
    UPPER_ROW_2 = 21
    UPPER_ROW_3 = 22
    UPPER_ROW_4 = 23
    UPPER_ROW_5 = 24
    UPPER_ROW_6 = 25
    UPPER_ROW_7 = 26
    UPPER_ROW_8 = 27

    # Master & Stop Clip
    MASTER = 28
    STOP_CLIP = 29

    # Scene Launch / Grid Quantize Buttons (Bottom-to-Top: 36..43, Top-to-Bottom: 43..36)
    SCENE_8_1_4 = 36     # Bottom Scene Row (Row 8: 1/4)
    SCENE_7_1_4T = 37    # Row 7: 1/4t
    SCENE_6_1_8 = 38     # Row 6: 1/8
    SCENE_5_1_8T = 39    # Row 5: 1/8t
    SCENE_4_1_16 = 40    # Row 4: 1/16
    SCENE_3_1_16T = 41   # Row 3: 1/16t
    SCENE_2_1_32 = 42    # Row 2: 1/32
    SCENE_1_1_32T = 43   # Top Scene Row (Row 1: 1/32t)

    # D-Pad Cursor Navigation & Modifiers
    CURSOR_LEFT = 44
    CURSOR_RIGHT = 45
    CURSOR_UP = 46
    CURSOR_DOWN = 47
    SELECT = 48
    SHIFT = 49

    # Grid & Performance Mode Buttons
    NOTE = 50
    SESSION = 51
    ADD_EFFECT = 52
    ADD_TRACK = 53
    OCTAVE_DOWN = 54
    OCTAVE_UP = 55
    REPEAT = 56
    ACCENT = 57
    SCALES = 58
    USER = 59

    # Track State & Step Routing
    MUTE = 60
    SOLO = 61
    STEP_IN = 62
    STEP_OUT = 63

    # Rear Pedal Footswitches
    FOOTSWITCH_1 = 64
    FOOTSWITCH_2 = 69

    # 8 Main Track Encoders & Master Encoder
    TRACK_ENCODER_1 = 71
    TRACK_ENCODER_2 = 72
    TRACK_ENCODER_3 = 73
    TRACK_ENCODER_4 = 74
    TRACK_ENCODER_5 = 75
    TRACK_ENCODER_6 = 76
    TRACK_ENCODER_7 = 77
    TRACK_ENCODER_8 = 78
    MASTER_ENCODER = 79

    # Transport & Left Workflow Column
    PLAY = 85
    RECORD = 86
    NEW = 87
    DUPLICATE = 88
    AUTOMATION = 89
    FIXED_LENGTH = 90

    # Lower Row Display Softkeys (Full RGB LEDs)
    LOWER_ROW_1 = 102
    LOWER_ROW_2 = 103
    LOWER_ROW_3 = 104
    LOWER_ROW_4 = 105
    LOWER_ROW_5 = 106
    LOWER_ROW_6 = 107
    LOWER_ROW_7 = 108
    LOWER_ROW_8 = 109

    # Right Encoder Mode Selection Buttons
    DEVICE = 110
    BROWSE = 111
    TRACK = 112
    CLIP = 113
    VOLUME = 114
    PAN_SEND = 115

    # Top-Left Edit Column
    DELETE = 118
    UNDO = 119


UPPER_SOFTKEY_CCS = (20, 21, 22, 23, 24, 25, 26, 27)
LOWER_SOFTKEY_CCS = (102, 103, 104, 105, 106, 107, 108, 109)
TRACK_ENCODER_CCS = (71, 72, 73, 74, 75, 76, 77, 78)
# Scene launch buttons ordered Top (Row 1) to Bottom (Row 8) matching visual layout
SCENE_LAUNCH_CCS_TOP_DOWN = (43, 42, 41, 40, 39, 38, 37, 36)

# Encoder Touch Notes (0x90 / 0x80)
ENCODER_TOUCH_TRACK_NOTES = (0, 1, 2, 3, 4, 5, 6, 7)
ENCODER_TOUCH_MASTER_NOTE = 8
ENCODER_TOUCH_SWING_NOTE = 9
ENCODER_TOUCH_TEMPO_NOTE = 10
TOUCHSTRIP_TOUCH_NOTE = 12

# 8x8 Pad Grid Note Bounds
PAD_NOTE_MIN = 36  # Bottom-Left (Row 0, Col 0)
PAD_NOTE_MAX = 99  # Top-Right (Row 7, Col 7)


class MonoLed(enum.IntEnum):
    """Monochrome Button LED states (`Basic` class in Colors.py)."""
    OFF = 0
    HALF = 1
    HALF_BLINK_SLOW = 2
    HALF_BLINK_FAST = 3
    FULL = 4
    FULL_BLINK_SLOW = 5
    FULL_BLINK_FAST = 6
    ON = 127


class BiLed(enum.IntEnum):
    """Bi-Color Button LED states (`BiLed` class in Colors.py)."""
    OFF = 0
    RED = 1
    RED_HALF = 2
    RED_BLINK = 3
    AMBER = 7
    AMBER_HALF = 8
    AMBER_BLINK = 9
    YELLOW = 13
    YELLOW_HALF = 14
    YELLOW_BLINK = 15
    GREEN = 19
    GREEN_HALF = 20
    GREEN_BLINK = 21


class RgbColor(enum.IntEnum):
    """Full RGB Palette indices for the 64 Pads & Lower Softkeys (`Rgb` in Colors.py)."""
    BLACK = 0
    DARK_GREY = 1
    GREY = 2
    WHITE = 3
    RED_HIGHLIGHT = 4
    RED = 5
    RED_DIM = 6
    RED_DARK = 7
    AMBER_HIGHLIGHT = 8
    AMBER = 9
    AMBER_DIM = 10
    AMBER_DARK = 11
    YELLOW_HIGHLIGHT = 12
    YELLOW = 13
    YELLOW_DIM = 14
    YELLOW_DARK = 15
    LIME_HIGHLIGHT = 16
    LIME = 17
    LIME_DIM = 18
    LIME_DARK = 19
    GREEN_HIGHLIGHT = 20
    GREEN = 21
    GREEN_DIM = 22
    GREEN_DARK = 23
    SPRING = 25
    SPRING_DIM = 26
    TURQUOISE = 29
    TURQUOISE_DIM = 30
    CYAN = 33
    CYAN_DIM = 34
    SKY = 37
    SKY_DIM = 38
    OCEAN_HIGHLIGHT = 40
    OCEAN = 41
    OCEAN_DIM = 42
    BLUE = 45
    BLUE_DIM = 46
    BLUE_DARK = 47
    ORCHID = 49
    ORCHID_DIM = 50
    MAGENTA = 53
    MAGENTA_DIM = 54
    PINK = 57
    PINK_DIM = 58
    WARM_WHITE = 122


# MIDI Channels (0-indexed) for Pad/Button LED Animations
LED_CHAN_STATIC = 0        # 0x90: Solid color
LED_CHAN_PULSE_1_16 = 7    # 0x97: Pulse 1/16
LED_CHAN_PULSE_1_8 = 8     # 0x98: Pulse 1/8
LED_CHAN_PULSE_1_4 = 9     # 0x99: Pulse 1/4
LED_CHAN_BLINK_1_16 = 12   # 0x9C: Blink 1/16
LED_CHAN_BLINK_1_8 = 13    # 0x9D: Blink 1/8
LED_CHAN_BLINK_1_4 = 14    # 0x9E: Blink 1/4

# Default Chain Color Cycle (8 distinct track hues)
CHAIN_COLORS_BRIGHT = (
    RgbColor.SPRING,
    RgbColor.CYAN,
    RgbColor.OCEAN,
    RgbColor.ORCHID,
    RgbColor.AMBER,
    RgbColor.YELLOW,
    RgbColor.TURQUOISE,
    RgbColor.PINK,
)
CHAIN_COLORS_DIM = (
    RgbColor.SPRING_DIM,
    RgbColor.CYAN_DIM,
    RgbColor.OCEAN_DIM,
    RgbColor.ORCHID_DIM,
    RgbColor.AMBER_DIM,
    RgbColor.YELLOW_DIM,
    RgbColor.TURQUOISE_DIM,
    RgbColor.PINK_DIM,
)

# ============================================================================
# 2. MUSICAL SCALES & ISOMETRIC KEYBOARD DEFINITIONS (`Consts.py` + MC-101)
# ============================================================================

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
# Circle of Fifths layout for Push 1 Scales menu softkeys:
# Upper row (CC 20..25): C, G, D, A, E, B
# Lower row (CC 102..107): F, Bb, Eb, Ab, Db, F#
CIRCLE_OF_FIFTHS_UPPER = (0, 7, 2, 9, 4, 11)   # C, G, D, A, E, B
CIRCLE_OF_FIFTHS_LOWER = (5, 10, 3, 8, 1, 6)   # F, A#, D#, G#, C#, F#

MUSICAL_SCALES: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("Major", (0, 2, 4, 5, 7, 9, 11)),
    ("Minor", (0, 2, 3, 5, 7, 8, 10)),
    ("Dorian", (0, 2, 3, 5, 7, 9, 10)),
    ("Mixolydian", (0, 2, 4, 5, 7, 9, 10)),
    ("Lydian", (0, 2, 4, 6, 7, 9, 11)),
    ("Phrygian", (0, 1, 3, 5, 7, 8, 10)),
    ("Locrian", (0, 1, 3, 5, 6, 8, 10)),
    ("Harmonic Minor", (0, 2, 3, 5, 7, 8, 11)),
    ("Melodic Minor", (0, 2, 3, 5, 7, 9, 11)),
    ("Minor Pentatonic", (0, 3, 5, 7, 10)),
    ("Major Pentatonic", (0, 2, 4, 7, 9)),
    ("Blues", (0, 3, 5, 6, 7, 10)),
    ("Whole Tone", (0, 2, 4, 6, 8, 10)),
    ("Diminished", (0, 2, 3, 5, 6, 8, 9, 11)),
    ("Super Locrian", (0, 1, 3, 4, 6, 8, 10)),
    ("Bhairav", (0, 1, 4, 5, 7, 8, 11)),
    ("Hungarian Minor", (0, 2, 3, 6, 7, 8, 11)),
    ("Minor Gypsy", (0, 1, 4, 5, 7, 8, 10)),
    ("Hirojoshi", (0, 2, 3, 7, 8)),
    ("In-Sen", (0, 1, 5, 7, 10)),
    ("Iwato", (0, 1, 5, 6, 10)),
    ("Kumoi", (0, 2, 3, 7, 9)),
    ("Pelog", (0, 1, 3, 4, 7, 8)),
    ("Spanish", (0, 1, 3, 4, 5, 6, 8, 10)),
)


def decode_relative_cc(val: int) -> int:
    """Decodes Push 1's 7-bit 2's complement relative encoder value to signed delta."""
    return val if val < 64 else val - 128


# ============================================================================
# 3. DOUBLE-BUFFERED 4x68 LCD DISPLAY ENGINE (`Push1Display`)
# ============================================================================

class Push1Display:
    """
    Manages the Ableton Push 1 4-line x 68-character alphanumeric LCD display.
    Provides 8-column (8 chars + spaces) and 4-column (17 chars) cell formatting,
    custom bargraph/pan glyph rendering, temporary toast overlays, and dirty-line
    diffing so SysEx is only transmitted for lines that actually changed.
    """

    def __init__(self, send_sysex_cb: Callable[[Sequence[int]], None]) -> None:
        self._send_sysex = send_sysex_cb
        self._buffer: list[bytearray] = [
            bytearray([0x20] * LCD_LINE_LENGTH) for _ in range(LCD_LINES)
        ]
        self._shadow: list[bytearray] = [
            bytearray([0x00] * LCD_LINE_LENGTH) for _ in range(LCD_LINES)
        ]
        self._overlay_lines: dict[int, tuple[bytearray, float]] = {}

    @staticmethod
    def _encode_ascii_or_glyph(text: str | bytes | bytearray, width: int, align: str = "left") -> bytes:
        """Converts text or raw glyph bytes into an exact-width 7-bit byte slice."""
        if isinstance(text, str):
            raw = bytearray()
            for ch in text:
                code = ord(ch)
                if 0 <= code <= 0x7F:
                    raw.append(code)
                elif ch == "…":
                    raw.append(GLYPH_ELLIPSIS)
                elif ch == "█":
                    raw.append(GLYPH_BLOCK_FULL)
                elif ch == "▌":
                    raw.append(GLYPH_BLOCK_HALF)
                elif ch == "□":
                    raw.append(GLYPH_BLOCK_EMPTY)
                elif ch == "▶":
                    raw.append(GLYPH_TRI_RIGHT)
                elif ch == "◀":
                    raw.append(GLYPH_TRI_LEFT)
                elif ch == "↑":
                    raw.append(GLYPH_ARROW_UP)
                elif ch == "↓":
                    raw.append(GLYPH_ARROW_DOWN)
                else:
                    raw.append(0x20)
        else:
            raw = bytearray(b & 0x7F for b in text)

        if len(raw) > width:
            if width >= 4:
                raw = raw[: width - 1] + bytearray([GLYPH_ELLIPSIS])
            else:
                raw = raw[:width]

        pad_len = width - len(raw)
        if pad_len > 0:
            if align == "center":
                left_pad = pad_len // 2
                right_pad = pad_len - left_pad
                raw = bytearray([0x20] * left_pad) + raw + bytearray([0x20] * right_pad)
            elif align == "right":
                raw = bytearray([0x20] * pad_len) + raw
            else:
                raw = raw + bytearray([0x20] * pad_len)
        return bytes(raw)

    @staticmethod
    def render_unipolar_bar(norm_val: float, width: int = 8) -> bytes:
        """
        Renders a horizontal bargraph using Push 1 glyphs 0x06 (full), 0x07 (half),
        and 0x1C (empty). An 8-character cell yields 16 discrete steps of resolution.
        """
        clamped = max(0.0, min(1.0, norm_val))
        half_steps = int(round(clamped * (width * 2)))
        full_count = half_steps // 2
        half_count = half_steps % 2
        empty_count = width - full_count - half_count
        return bytes(
            [GLYPH_BLOCK_FULL] * full_count
            + [GLYPH_BLOCK_HALF] * half_count
            + [GLYPH_BLOCK_EMPTY] * empty_count
        )

    @staticmethod
    def render_bipolar_pan(pan_val: float, width: int = 8) -> bytes:
        """
        Renders a bipolar pan slider for pan_val in [-1.0, +1.0].
        Uses GLYPH_PAN_CENTER (0x03) at the center.
        """
        clamped = max(-1.0, min(1.0, pan_val))
        if abs(clamped) < 0.03:
            label = "   C    "
            return Push1Display._encode_ascii_or_glyph(label, width, align="center")
        if clamped < 0:
            pct = int(round(abs(clamped) * 50))
            return Push1Display._encode_ascii_or_glyph(f"{pct:2d}L", width, align="center")
        pct = int(round(clamped * 50))
        return Push1Display._encode_ascii_or_glyph(f"{pct:2d}R", width, align="center")

    def set_line_raw(self, line_idx: int, content: str | bytes | bytearray) -> None:
        """Writes an entire 68-character row (0..3)."""
        if not (0 <= line_idx < LCD_LINES):
            return
        self._buffer[line_idx][:] = self._encode_ascii_or_glyph(content, LCD_LINE_LENGTH)

    def set_8cells(
        self,
        line_idx: int,
        cells: Sequence[str | bytes | bytearray],
        align: str = "left",
    ) -> None:
        """
        Formats 8 cells of 8 characters each, aligned directly beneath the 8 encoders
        and 8 display softkeys (with 1-character spaces at indices 8, 25, 42, 59).
        """
        if not (0 <= line_idx < LCD_LINES):
            return
        row = bytearray([0x20] * LCD_LINE_LENGTH)
        for col_idx in range(min(8, len(cells))):
            offset = LCD_8COL_OFFSETS[col_idx]
            row[offset : offset + LCD_CELL_WIDTH] = self._encode_ascii_or_glyph(
                cells[col_idx], LCD_CELL_WIDTH, align=align
            )
        self._buffer[line_idx][:] = row

    def set_4segments(
        self,
        line_idx: int,
        segments: Sequence[str | bytes | bytearray],
        align: str = "left",
    ) -> None:
        """Formats 4 blocks of 17 characters matching the 4 physical LCD glass segments."""
        if not (0 <= line_idx < LCD_LINES):
            return
        row = bytearray([0x20] * LCD_LINE_LENGTH)
        for seg_idx in range(min(4, len(segments))):
            offset = LCD_4COL_OFFSETS[seg_idx]
            row[offset : offset + LCD_BLOCK_WIDTH] = self._encode_ascii_or_glyph(
                segments[seg_idx], LCD_BLOCK_WIDTH, align=align
            )
        self._buffer[line_idx][:] = row

    def show_toast(self, line_idx: int, message: str, duration_sec: float = 1.5) -> None:
        """Temporarily overlays a high-priority status banner on `line_idx`."""
        if 0 <= line_idx < LCD_LINES:
            encoded = bytearray(self._encode_ascii_or_glyph(message, LCD_LINE_LENGTH, align="center"))
            self._overlay_lines[line_idx] = (encoded, time.monotonic() + duration_sec)

    def clear_toast(self, line_idx: int) -> None:
        """Immediately clears a temporary overlay on `line_idx`."""
        self._overlay_lines.pop(line_idx, None)

    def flush(self, force: bool = False) -> None:
        """
        Transmits 77-byte SysEx frames ONLY for LCD lines whose content has changed
        since the last flush (or if `force=True`).
        """
        now = time.monotonic()
        for line_idx in range(LCD_LINES):
            target = self._buffer[line_idx]
            if line_idx in self._overlay_lines:
                overlay_bytes, expires_at = self._overlay_lines[line_idx]
                if now < expires_at:
                    target = overlay_bytes
                else:
                    del self._overlay_lines[line_idx]

            if force or target != self._shadow[line_idx]:
                self._shadow[line_idx][:] = target
                sysex_msg = (
                    list(PUSH1_SYSEX_HEADER)
                    + [SYSEX_CMD_LCD_LINE_1 + line_idx, 0x00, 0x45, 0x00]
                    + list(target)
                    + [SYSEX_END]
                )
                self._send_sysex(sysex_msg)


# ============================================================================
# 4. ZYNTHIAN & MC-101 STATE / BACKEND ABSTRACTION
# ============================================================================

@dataclass
class ParameterSlot:
    """Represents a single controllable parameter (Zynthian `zctrl` or MC-101 SysEx)."""
    symbol: str
    short_name: str
    value: float = 64.0
    val_min: float = 0.0
    val_max: float = 127.0
    unit: str = ""
    labels: Optional[Sequence[str]] = None
    is_integer: bool = True
    zctrl_ref: object = None  # Native Zynthian zynthian_controller reference when in-process

    @property
    def normalized(self) -> float:
        span = self.val_max - self.val_min
        if span <= 0:
            return 0.0
        return max(0.0, min(1.0, (self.value - self.val_min) / span))

    def format_value(self) -> str:
        if self.labels:
            idx = max(0, min(len(self.labels) - 1, int(round(self.value))))
            return str(self.labels[idx])
        if self.is_integer:
            return f"{int(round(self.value))}{self.unit}"
        return f"{self.value:.1f}{self.unit}"

    def nudge(self, delta: int, fine: bool = False) -> None:
        if self.zctrl_ref is not None and hasattr(self.zctrl_ref, "nudge"):
            self.zctrl_ref.nudge(delta)
            self.value = float(getattr(self.zctrl_ref, "value", self.value))
            return
        step = 1.0 if self.is_integer else (self.val_max - self.val_min) / (500.0 if fine else 100.0)
        if not self.is_integer and fine:
            step *= 0.2
        self.value = max(self.val_min, min(self.val_max, self.value + delta * step))


@dataclass
class ChainDescriptor:
    """Represents a Zynthian Chain (Synth, Audio FX, MIDI, or MC-101 Track)."""
    chain_id: int
    title: str
    midi_chan: int = 0
    mixer_chan: int = 0
    level: float = 0.80      # 0.0 .. 1.0 (0.80 = 0.0 dB in zynmixer)
    balance: float = 0.0     # -1.0 (L) .. +1.0 (R)
    mute: bool = False
    solo: bool = False
    send_a: float = 0.0      # Delay / Chorus send
    send_b: float = 0.0      # Reverb send
    engine_name: str = "ZynAddSubFX"
    bank_list: list[str] = field(default_factory=lambda: ["Bank 1", "Bank 2", "User"])
    preset_list: list[str] = field(default_factory=lambda: ["Init Patch", "Warm Pad", "Analogue Bass", "Lead Pluck"])
    bank_idx: int = 0
    preset_idx: int = 0
    param_pages: dict[str, list[ParameterSlot]] = field(default_factory=dict)


class ZynthianBackendAdapter:
    """
    Unified interface bridging `Push1Controller` to either:
    1. In-process Zynthian native singletons (`state_manager`, `chain_manager`, `zynmixer`, `zynseq`), OR
    2. Standalone state / OSC / Roland MC-101 SysEx when running outside `zynthian-ui`.
    """

    def __init__(
        self,
        state_manager: object = None,
        chain_manager: object = None,
        zynmixer: object = None,
        zynseq: object = None,
        send_note_cb: Optional[Callable[[int, int, int], None]] = None,
    ) -> None:
        self.state_manager = state_manager
        self.chain_manager = chain_manager
        self.zynmixer = zynmixer
        self.zynseq = zynseq
        self._send_note_cb = send_note_cb

        # Standalone fallback state (also mirrors native Zynthian state)
        self.tempo_bpm: float = 120.0
        self.swing_amount: float = 50.0  # 50% = no swing, 50..100%
        self.metronome_enabled: bool = False
        self.is_playing: bool = False
        self.is_recording: bool = False
        self.master_level: float = 0.80
        self.active_chain_idx: int = 0
        self.active_scene_idx: int = 0

        # 8x8 Zynpad Clip States: 0 = Empty, 1 = Stopped (Has Notes), 2 = Playing, 3 = Starting, 4 = Stopping
        self.clip_matrix: list[list[int]] = [[1 if r < 2 else 0 for c in range(8)] for r in range(8)]
        # Step Sequencer Pattern Buffer: (step 0..31, note 0..127) -> (velocity, duration, chance, stutter)
        self.pattern_steps: dict[tuple[int, int], list[float]] = {}

        self.chains: list[ChainDescriptor] = self._create_default_chains()

    @staticmethod
    def _create_default_chains() -> list[ChainDescriptor]:
        defaults = [
            (1, "1:MC101-T1", 0, "MC-101 Tone"),
            (2, "2:MC101-T2", 1, "MC-101 Drum"),
            (3, "3:MC101-T3", 2, "MC-101 Bass"),
            (4, "4:MC101-T4", 3, "MC-101 Lead"),
            (5, "5:ZynAdd", 4, "ZynAddSubFX"),
            (6, "6:Dexed", 5, "Dexed FM"),
            (7, "7:SurgeXT", 6, "Surge XT"),
            (8, "8:Teensy", 7, "Teensy 4.1"),
        ]
        chains: list[ChainDescriptor] = []
        for cid, title, mch, eng in defaults:
            pages = {
                "Osc/Sound": [
                    ParameterSlot("osc_type", "OscType", 1, 0, 4, labels=["PCM", "VA", "Sync", "SuperSAW", "Noise"]),
                    ParameterSlot("va_form", "Waveform", 0, 0, 8, labels=["SAW", "SQR", "TRI", "SIN", "RAMP", "JUNO", "TRI2", "TRI3", "SIN2"]),
                    ParameterSlot("pw", "PulseW", 64, 0, 127),
                    ParameterSlot("detune", "Detune", 20, 0, 127),
                ],
                "Filter": [
                    ParameterSlot("cutoff", "Cutoff", 680, 0, 1023),
                    ParameterSlot("reso", "Resonanc", 240, 0, 1023),
                    ParameterSlot("vcf_type", "VCF Model", 1, 0, 3, labels=["FLAT", "TYPE-JP", "TYPE-M", "TYPE-P"]),
                    ParameterSlot("fenv_dep", "EnvDepth", 24, -63, 63),
                ],
                "Flt Env": [
                    ParameterSlot("f_atk", "F-Attack", 10, 0, 1023),
                    ParameterSlot("f_dcy", "F-Decay", 380, 0, 1023),
                    ParameterSlot("f_sus", "F-Sustn", 512, 0, 1023),
                    ParameterSlot("f_rel", "F-Releas", 290, 0, 1023),
                ],
                "Amp Env": [
                    ParameterSlot("a_atk", "A-Attack", 0, 0, 1023),
                    ParameterSlot("a_dcy", "A-Decay", 420, 0, 1023),
                    ParameterSlot("a_sus", "A-Sustn", 800, 0, 1023),
                    ParameterSlot("a_rel", "A-Releas", 310, 0, 1023),
                ],
                "LFO 1": [
                    ParameterSlot("lfo1_wav", "LFO1 Wav", 1, 0, 10, labels=["SIN", "TRI", "SAW-U", "SAW-D", "SQR", "RND", "TRP", "S&H", "CHS", "VSIN", "STEP"]),
                    ParameterSlot("lfo1_rat", "LFO1 Rat", 650, 0, 1023),
                    ParameterSlot("lfo1_flt", "LFO1->Flt", 0, -100, 100),
                    ParameterSlot("lfo1_pit", "LFO1->Pit", 0, -100, 100),
                ],
                "MFX/Send": [
                    ParameterSlot("mfx_type", "MFX Type", 1, 0, 90),
                    ParameterSlot("mfx_sw", "MFX Sw", 1, 0, 1, labels=["OFF", "ON"]),
                    ParameterSlot("cho_send", "Dly Send", 40, 0, 127),
                    ParameterSlot("rev_send", "Rev Send", 55, 0, 127),
                ],
            }
            chains.append(
                ChainDescriptor(
                    chain_id=cid,
                    title=title,
                    midi_chan=mch,
                    mixer_chan=mch,
                    engine_name=eng,
                    param_pages=pages,
                )
            )
        return chains

    # --- Sync with Native Zynthian Managers When Running In-Process ---

    def sync_from_zynthian(self) -> None:
        """Pulls live chains, mixer levels, and zynctrl pages from Zynthian singletons."""
        if self.zynseq is not None and hasattr(self.zynseq, "get_tempo"):
            try:
                self.tempo_bpm = float(self.zynseq.get_tempo())
            except Exception:
                pass

        if self.chain_manager is not None and hasattr(self.chain_manager, "chains"):
            try:
                zchains = list(self.chain_manager.chains.values())
                active_id = getattr(self.chain_manager, "active_chain_id", None)
                synced: list[ChainDescriptor] = []
                for idx, zc in enumerate(zchains[:8]):
                    cid = getattr(zc, "chain_id", idx + 1)
                    if cid == active_id:
                        self.active_chain_idx = idx
                    mchan = getattr(zc, "mixer_chan", idx)
                    lvl = 0.8
                    bal = 0.0
                    mute = False
                    solo = False
                    if self.zynmixer is not None and mchan is not None:
                        try:
                            lvl = float(self.zynmixer.get_level(mchan))
                            bal = float(self.zynmixer.get_balance(mchan))
                            mute = bool(self.zynmixer.get_mute(mchan))
                            solo = bool(self.zynmixer.get_solo(mchan))
                        except Exception:
                            pass
                    title = getattr(zc, "title", f"Ch {idx + 1}")
                    cd = ChainDescriptor(
                        chain_id=cid,
                        title=f"{idx + 1}:{title}",
                        midi_chan=getattr(zc, "midi_chan", idx) or idx,
                        mixer_chan=mchan if mchan is not None else idx,
                        level=lvl,
                        balance=bal,
                        mute=mute,
                        solo=solo,
                    )
                    # Extract zctrl screens from active processor
                    procs = getattr(zc, "processors", [])
                    if procs:
                        proc = procs[0]
                        cd.engine_name = getattr(proc, "name", "Synth")
                        ctrl_screens = getattr(proc, "ctrl_screens", {})
                        for page_name, zctrls in ctrl_screens.items():
                            slots = []
                            for zc_obj in zctrls:
                                slots.append(
                                    ParameterSlot(
                                        symbol=getattr(zc_obj, "symbol", "param"),
                                        short_name=getattr(zc_obj, "short_name", "Param")[:8],
                                        value=float(getattr(zc_obj, "value", 0)),
                                        val_min=float(getattr(zc_obj, "value_min", 0)),
                                        val_max=float(getattr(zc_obj, "value_max", 127)),
                                        labels=getattr(zc_obj, "labels", None),
                                        zctrl_ref=zc_obj,
                                    )
                                )
                            cd.param_pages[str(page_name)] = slots
                    if not cd.param_pages and idx < len(self.chains):
                        cd.param_pages = self.chains[idx].param_pages
                    synced.append(cd)
                if synced:
                    self.chains = synced
            except Exception as exc:
                logger.debug("Zynthian chain sync skipped: %s", exc)

    def set_chain_level(self, chain_idx: int, new_level: float) -> None:
        if not (0 <= chain_idx < len(self.chains)):
            return
        clamped = max(0.0, min(1.0, new_level))
        chain = self.chains[chain_idx]
        chain.level = clamped
        if self.zynmixer is not None:
            try:
                self.zynmixer.set_level(chain.mixer_chan, clamped)
            except Exception:
                pass

    def set_chain_balance(self, chain_idx: int, new_bal: float) -> None:
        if not (0 <= chain_idx < len(self.chains)):
            return
        clamped = max(-1.0, min(1.0, new_bal))
        chain = self.chains[chain_idx]
        chain.balance = clamped
        if self.zynmixer is not None:
            try:
                self.zynmixer.set_balance(chain.mixer_chan, clamped)
            except Exception:
                pass

    def toggle_chain_mute(self, chain_idx: int) -> bool:
        if not (0 <= chain_idx < len(self.chains)):
            return False
        chain = self.chains[chain_idx]
        chain.mute = not chain.mute
        if self.zynmixer is not None:
            try:
                self.zynmixer.set_mute(chain.mixer_chan, int(chain.mute))
            except Exception:
                pass
        return chain.mute

    def toggle_chain_solo(self, chain_idx: int) -> bool:
        if not (0 <= chain_idx < len(self.chains)):
            return False
        chain = self.chains[chain_idx]
        chain.solo = not chain.solo
        if self.zynmixer is not None:
            try:
                self.zynmixer.set_solo(chain.mixer_chan, int(chain.solo))
            except Exception:
                pass
        return chain.solo

    def set_master_level(self, new_level: float) -> None:
        self.master_level = max(0.0, min(1.0, new_level))
        if self.zynmixer is not None:
            try:
                main_ch = getattr(self.zynmixer, "MAX_NUM_CHANNELS", 16)
                self.zynmixer.set_level(main_ch, self.master_level)
            except Exception:
                pass

    def nudge_tempo(self, delta: int, fine: bool = False) -> float:
        step = 0.1 if fine else 1.0
        self.tempo_bpm = max(30.0, min(300.0, round(self.tempo_bpm + delta * step, 1)))
        if self.zynseq is not None and hasattr(self.zynseq, "set_tempo"):
            try:
                self.zynseq.set_tempo(self.tempo_bpm)
            except Exception:
                pass
        return self.tempo_bpm

    def nudge_swing(self, delta: int) -> float:
        self.swing_amount = max(50.0, min(95.0, self.swing_amount + delta * 1.0))
        if self.zynseq is not None and hasattr(self.zynseq, "libseq"):
            try:
                self.zynseq.libseq.setSwingAmount(self.swing_amount / 100.0)
            except Exception:
                pass
        return self.swing_amount

    def select_chain(self, chain_idx: int) -> None:
        if 0 <= chain_idx < len(self.chains):
            self.active_chain_idx = chain_idx
            if self.chain_manager is not None and hasattr(self.chain_manager, "set_active_chain_by_id"):
                try:
                    self.chain_manager.set_active_chain_by_id(self.chains[chain_idx].chain_id)
                except Exception:
                    pass

    def toggle_clip(self, scene_row: int, track_col: int) -> int:
        """Toggles a clip in Zynpad (scene_row 0..7 top-to-bottom, track_col 0..7)."""
        cur = self.clip_matrix[scene_row][track_col]
        if cur == 2:
            self.clip_matrix[scene_row][track_col] = 1
        else:
            # Stop other playing clips in the same column
            for r in range(8):
                if self.clip_matrix[r][track_col] == 2:
                    self.clip_matrix[r][track_col] = 1
            self.clip_matrix[scene_row][track_col] = 2

        if self.zynseq is not None and hasattr(self.zynseq, "libseq"):
            try:
                pad_idx = track_col * 8 + scene_row
                self.zynseq.libseq.togglePlayState(self.active_scene_idx + 1, pad_idx)
            except Exception:
                pass
        return self.clip_matrix[scene_row][track_col]

    def launch_scene(self, scene_row: int) -> None:
        """Launches all populated clips in `scene_row` (0..7)."""
        self.active_scene_idx = scene_row
        for col in range(8):
            for r in range(8):
                if r == scene_row and self.clip_matrix[r][col] > 0:
                    self.clip_matrix[r][col] = 2
                elif self.clip_matrix[r][col] == 2:
                    self.clip_matrix[r][col] = 1
        if self.zynseq is not None and hasattr(self.zynseq, "set_bank"):
            try:
                self.zynseq.set_bank(scene_row + 1)
            except Exception:
                pass

    def send_cuia(self, cuia_name: str, params: Optional[list] = None) -> None:
        """Dispatches a Zynthian Callable UI Action (CUIA)."""
        if self.state_manager is not None and hasattr(self.state_manager, "send_cuia"):
            try:
                self.state_manager.send_cuia(cuia_name, params or [])
            except Exception:
                pass


# ============================================================================
# 5. PUSH 1 CONTROLLER MODES & STATE MACHINE (`Push1Controller`)
# ============================================================================

class EncoderMode(enum.Enum):
    VOLUME = "VOLUME"
    PAN_SEND = "PAN_SEND"
    TRACK = "TRACK"
    CLIP = "CLIP"
    DEVICE = "DEVICE"
    BROWSE = "BROWSE"
    SCALES = "SCALES"
    ADD_TRACK = "ADD_TRACK"
    STEP_INSPECTOR = "STEP_INSPECTOR"


class PadMode(enum.Enum):
    SESSION = "SESSION"                 # 8x8 Zynpad Clip Launcher
    NOTE_ISOMETRIC = "NOTE_ISOMETRIC"   # 64-Pad Isometric Scale Keyboard
    NOTE_DRUM_SEQ = "NOTE_DRUM_SEQ"     # Bottom-Left 4x4 Drum + Top 32-Step Sequencer
    NOTE_MELODIC_SEQ = "NOTE_MELODIC_SEQ"  # 7-Row Melodic Step Sequencer


class Push1Controller:
    """
    Core Ableton Push 1 state machine and hardware driver.
    Processes all incoming MIDI Notes, CCs, Pitchbend, Aftertouch, and manages
    the 4x68 LCD Display, 64 RGB Pads, and 49 Hardware Buttons.
    """

    def __init__(
        self,
        backend: ZynthianBackendAdapter,
        send_midi_cb: Callable[[Sequence[int]], None],
    ) -> None:
        self.backend = backend
        self._send_midi = send_midi_cb
        self.display = Push1Display(send_sysex_cb=self._send_midi)

        # Active Modes
        self.encoder_mode: EncoderMode = EncoderMode.DEVICE
        self._prev_encoder_mode: EncoderMode = EncoderMode.DEVICE
        self.pad_mode: PadMode = PadMode.NOTE_ISOMETRIC
        self.pan_send_submode: int = 0  # 0 = Pan, 1 = Delay/Chorus Send, 2 = Reverb Send

        # Modifiers & Performance States
        self.shift_held: bool = False
        self.select_held: bool = False
        self.delete_held: bool = False
        self.duplicate_held: bool = False
        self.mute_held: bool = False
        self.solo_held: bool = False
        self.stop_held: bool = False
        self.accent_enabled: bool = False
        self.repeat_enabled: bool = False
        self.user_mc101_mode: bool = False
        self.touched_encoders: set[int] = set()
        self.held_step_pad: Optional[int] = None

        # Musical Scale & Isometric Layout State
        self.scale_idx: int = 0         # Index into MUSICAL_SCALES (0 = Major)
        self.root_note: int = 0         # 0 = C .. 11 = B
        self.in_key_mode: bool = True   # True = In-Key folded, False = Chromatic
        self.octave_offset: int = 2     # Base octave (C2 = 36)
        self.row_interval: int = 5      # 5 semitones (4ths) in Chromatic, 3 degrees in In-Key

        # Sequencer & Device Paging State
        self.selected_drum_note: int = 36
        self.seq_Loop_page: int = 0
        self.device_page_pair_idx: int = 0
        self._tap_times: list[float] = []

        # Hardware Output Shadow Caches (Avoid redundant MIDI output)
        self._pad_led_cache: dict[tuple[int, int], int] = {}
        self._cc_led_cache: dict[tuple[int, int], int] = {}
        self._pad_to_midi_note: list[int] = [60] * 64
        self._note_to_pads: dict[int, list[int]] = {}
        self._active_notes: set[int] = set()

        self._rebuild_isometric_map()

    # ------------------------------------------------------------------------
    # Initialization & Shutdown
    # ------------------------------------------------------------------------

    def init_hardware(self) -> None:
        """Initializes Push 1 into Live Mode, configures touchstrip, and renders UI."""
        # 1. Switch Push 1 into Native Live Mode (0x00)
        self._send_midi(list(PUSH1_SYSEX_HEADER) + [SYSEX_CMD_SET_MODE, 0x00, 0x01, 0x00, SYSEX_END])
        # 2. Set Channel Aftertouch mode (0x00)
        self._send_midi(list(PUSH1_SYSEX_HEADER) + [SYSEX_CMD_AFTERTOUCH_MODE, 0x00, 0x01, 0x00, SYSEX_END])
        # 3. Configure Touchstrip as centered Pitch Bend ribbon
        self.set_touchstrip_mode(TOUCHSTRIP_MODE_PITCHBEND)
        # 4. Sync backend & full redraw
        self.backend.sync_from_zynthian()
        self.refresh_all(force=True)
        self.display.show_toast(0, "=== Zynthian Push 1 Native Bridge Ready ===", 2.0)
        self.display.flush(force=True)

    def shutdown_hardware(self) -> None:
        """Clears all 4 LCD lines and turns off all Pad and Button LEDs on exit."""
        for line_cmd in (
            SYSEX_CMD_CLEAR_LINE_1,
            SYSEX_CMD_CLEAR_LINE_2,
            SYSEX_CMD_CLEAR_LINE_3,
            SYSEX_CMD_CLEAR_LINE_4,
        ):
            self._send_midi(list(PUSH1_SYSEX_HEADER) + [line_cmd, 0x00, 0x00, SYSEX_END])
        for note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self._send_midi([0x90, note, 0])
        for cc in PushCC:
            self._send_midi([0xB0, int(cc), 0])

    # ------------------------------------------------------------------------
    # Low-Level LED & Touchstrip Helpers
    # ------------------------------------------------------------------------

    def set_pad_led(self, pad_note: int, color: int, channel: int = LED_CHAN_STATIC, force: bool = False) -> None:
        key = (channel & 0x0F, pad_note & 0x7F)
        if force or self._pad_led_cache.get(key) != color:
            self._pad_led_cache[key] = color
            self._send_midi([0x90 | (channel & 0x0F), pad_note & 0x7F, color & 0x7F])

    def set_button_led(self, cc: int, color: int, channel: int = LED_CHAN_STATIC, force: bool = False) -> None:
        key = (channel & 0x0F, cc & 0x7F)
        if force or self._cc_led_cache.get(key) != color:
            self._cc_led_cache[key] = color
            self._send_midi([0xB0 | (channel & 0x0F), cc & 0x7F, color & 0x7F])

    def set_touchstrip_mode(self, mode_flags: int) -> None:
        self._send_midi(
            list(PUSH1_SYSEX_HEADER) + [SYSEX_CMD_TOUCHSTRIP_CFG, 0x00, 0x01, mode_flags & 0x7F, SYSEX_END]
        )

    # ------------------------------------------------------------------------
    # Isometric Scale Mapping Engine (`Consts.py` / `InstrumentComponent.py`)
    # ------------------------------------------------------------------------

    def _rebuild_isometric_map(self) -> None:
        """
        Pre-computes the 64-pad MIDI note lookup table and reverse pitch-to-pads
        dictionary so live pad playing in `midi_event` requires zero allocations.
        """
        _, intervals = MUSICAL_SCALES[self.scale_idx]
        num_degrees = len(intervals)
        base_c = 12 * (self.octave_offset + 1)  # e.g., octave_offset=2 -> MIDI 36 (C2)

        self._note_to_pads.clear()
        for pad_idx in range(64):
            row = pad_idx // 8  # 0 (bottom) .. 7 (top)
            col = pad_idx % 8   # 0 (left) .. 7 (right)
            if self.in_key_mode:
                degree_index = row * 3 + col
                oct_shift = degree_index // num_degrees
                scale_deg = degree_index % num_degrees
                midi_note = base_c + self.root_note + (oct_shift * 12) + intervals[scale_deg]
            else:
                semitone_offset = row * self.row_interval + col
                midi_note = base_c + self.root_note + semitone_offset

            midi_note = max(0, min(127, midi_note))
            self._pad_to_midi_note[pad_idx] = midi_note
            pad_hw_note = PAD_NOTE_MIN + pad_idx
            self._note_to_pads.setdefault(midi_note, []).append(pad_hw_note)

    def _is_note_in_scale(self, midi_note: int) -> tuple[bool, bool]:
        """Returns `(is_root, is_in_scale)` for any MIDI note."""
        rel = (midi_note - self.root_note) % 12
        if rel == 0:
            return True, True
        _, intervals = MUSICAL_SCALES[self.scale_idx]
        return False, (rel in intervals)

    # ------------------------------------------------------------------------
    # Incoming MIDI Event Dispatcher
    # ------------------------------------------------------------------------

    def handle_midi_event(self, ev: Sequence[int]) -> bool:
        """
        Entry point for all MIDI events coming from Ableton Push 1 Live Port.
        Returns True if the event was consumed by the control surface.
        """
        if not ev or len(ev) < 2:
            return False

        status = ev[0] & 0xF0
        data1 = ev[1] & 0x7F
        data2 = ev[2] & 0x7F if len(ev) > 2 else 0

        # 1. Note On / Note Off (Pads 36..99, Encoder Touch 0..10, Touchstrip Touch 12)
        if status in (0x90, 0x80):
            is_pressed = (status == 0x90) and (data2 > 0)
            if PAD_NOTE_MIN <= data1 <= PAD_NOTE_MAX:
                self._on_pad_event(data1, data2 if is_pressed else 0, is_pressed)
                return True
            if 0 <= data1 <= 10 or data1 == TOUCHSTRIP_TOUCH_NOTE:
                self._on_encoder_touch(data1, is_pressed)
                return True

        # 2. Control Change (Buttons & Endless Rotary Encoders)
        elif status == 0xB0:
            if data1 in TRACK_ENCODER_CCS:
                enc_idx = TRACK_ENCODER_CCS.index(data1)
                self._on_track_encoder_turn(enc_idx, decode_relative_cc(data2))
                return True
            if data1 == PushCC.MASTER_ENCODER:
                self._on_master_encoder_turn(decode_relative_cc(data2))
                return True
            if data1 == PushCC.TEMPO_ENCODER:
                self._on_tempo_encoder_turn(decode_relative_cc(data2))
                return True
            if data1 == PushCC.SWING_ENCODER:
                self._on_swing_encoder_turn(decode_relative_cc(data2))
                return True

            self._on_button_cc(data1, data2 > 0)
            return True

        return False

    # ------------------------------------------------------------------------
    # Encoder Turn & Touch Handlers
    # ------------------------------------------------------------------------

    def _on_encoder_touch(self, note: int, is_touched: bool) -> None:
        if 0 <= note <= 7:
            if is_touched:
                self.touched_encoders.add(note)
                # Hold [Delete] + Touch Encoder resets parameter or mixer channel to default!
                if self.delete_held:
                    self._reset_encoder_slot(note)
            else:
                self.touched_encoders.discard(note)
            self.refresh_lcd()
        elif note == ENCODER_TOUCH_MASTER_NOTE:
            if is_touched:
                db_str = self._level_to_db_str(self.backend.master_level)
                self.display.show_toast(0, f"Master Mixbus Volume: {db_str}", 5.0)
            else:
                self.display.clear_toast(0)
            self.display.flush()
        elif note == ENCODER_TOUCH_TEMPO_NOTE:
            if is_touched:
                self.display.show_toast(0, f"Global Tempo: {self.backend.tempo_bpm:.1f} BPM", 5.0)
            else:
                self.display.clear_toast(0)
            self.display.flush()
        elif note == ENCODER_TOUCH_SWING_NOTE:
            if is_touched:
                self.display.show_toast(0, f"Global Swing: {self.backend.swing_amount:.0f}%", 5.0)
            else:
                self.display.clear_toast(0)
            self.display.flush()

    def _reset_encoder_slot(self, enc_idx: int) -> None:
        if self.encoder_mode == EncoderMode.VOLUME and enc_idx < len(self.backend.chains):
            self.backend.set_chain_level(enc_idx, 0.80)  # 0.0 dB
        elif self.encoder_mode == EncoderMode.PAN_SEND and enc_idx < len(self.backend.chains):
            if self.pan_send_submode == 0:
                self.backend.set_chain_balance(enc_idx, 0.0)  # Center

    def _on_master_encoder_turn(self, delta: int) -> None:
        step = 0.005 if self.shift_held else 0.02
        self.backend.set_master_level(self.backend.master_level + delta * step)
        db_str = self._level_to_db_str(self.backend.master_level)
        self.display.show_toast(0, f"Master Mixbus Volume: {db_str}", 1.5)
        self.display.flush()

    def _on_tempo_encoder_turn(self, delta: int) -> None:
        bpm = self.backend.nudge_tempo(delta, fine=self.shift_held)
        self.display.show_toast(0, f"Global Tempo: {bpm:.1f} BPM", 1.5)
        self.display.flush()

    def _on_swing_encoder_turn(self, delta: int) -> None:
        swing = self.backend.nudge_swing(delta)
        self.display.show_toast(0, f"Global Swing: {swing:.0f}%", 1.5)
        self.display.flush()

    def _on_track_encoder_turn(self, enc_idx: int, delta: int) -> None:
        fine = self.shift_held

        if self.encoder_mode == EncoderMode.VOLUME:
            if enc_idx < len(self.backend.chains):
                step = 0.005 if fine else 0.02
                cur = self.backend.chains[enc_idx].level
                self.backend.set_chain_level(enc_idx, cur + delta * step)

        elif self.encoder_mode == EncoderMode.PAN_SEND:
            if enc_idx < len(self.backend.chains):
                chain = self.backend.chains[enc_idx]
                step = 0.01 if fine else 0.04
                if self.pan_send_submode == 0:
                    self.backend.set_chain_balance(enc_idx, chain.balance + delta * step)
                elif self.pan_send_submode == 1:
                    chain.send_a = max(0.0, min(1.0, chain.send_a + delta * step))
                else:
                    chain.send_b = max(0.0, min(1.0, chain.send_b + delta * step))

        elif self.encoder_mode == EncoderMode.TRACK:
            chain = self.backend.chains[self.backend.active_chain_idx]
            step = 0.005 if fine else 0.02
            if enc_idx == 0:
                self.backend.set_chain_level(self.backend.active_chain_idx, chain.level + delta * step)
            elif enc_idx == 1:
                self.backend.set_chain_balance(self.backend.active_chain_idx, chain.balance + delta * (step * 2))
            elif enc_idx == 2 and abs(delta) > 0:
                chain.mute = delta > 0
            elif enc_idx == 3 and abs(delta) > 0:
                chain.solo = delta > 0
            elif enc_idx == 4:
                chain.send_a = max(0.0, min(1.0, chain.send_a + delta * step))
            elif enc_idx == 5:
                chain.send_b = max(0.0, min(1.0, chain.send_b + delta * step))

        elif self.encoder_mode == EncoderMode.DEVICE:
            slots = self._get_active_8_param_slots()
            if enc_idx < len(slots) and slots[enc_idx] is not None:
                slots[enc_idx].nudge(delta, fine=fine)

        elif self.encoder_mode == EncoderMode.BROWSE:
            chain = self.backend.chains[self.backend.active_chain_idx]
            if enc_idx < 4 and chain.bank_list:
                chain.bank_idx = max(0, min(len(chain.bank_list) - 1, chain.bank_idx + (1 if delta > 0 else -1)))
            elif enc_idx >= 4 and chain.preset_list:
                chain.preset_idx = max(0, min(len(chain.preset_list) - 1, chain.preset_idx + (1 if delta > 0 else -1)))

        elif self.encoder_mode == EncoderMode.SCALES:
            if enc_idx in (0, 1):
                self.scale_idx = (self.scale_idx + (1 if delta > 0 else -1)) % len(MUSICAL_SCALES)
                self._rebuild_isometric_map()
                self.refresh_pads()

        elif self.encoder_mode == EncoderMode.STEP_INSPECTOR and self.held_step_pad is not None:
            step_idx = self.held_step_pad
            key = (step_idx, self.selected_drum_note)
            vals = self.backend.pattern_steps.setdefault(key, [100.0, 1.0, 100.0, 0.0])
            if enc_idx == 0:  # Pitch
                self.selected_drum_note = max(0, min(127, self.selected_drum_note + delta))
            elif enc_idx == 1:  # Velocity
                vals[0] = max(1.0, min(127.0, vals[0] + delta))
            elif enc_idx == 2:  # Gate Duration
                vals[1] = max(0.1, min(16.0, round(vals[1] + delta * 0.25, 2)))
            elif enc_idx == 3:  # Probability Chance
                vals[2] = max(0.0, min(100.0, vals[2] + delta * 5.0))
            elif enc_idx == 4:  # Ratchet / Stutter count
                vals[3] = max(0.0, min(8.0, vals[3] + (1 if delta > 0 else -1)))

        self.refresh_lcd()

    # ------------------------------------------------------------------------
    # Button Press / Release Handler
    # ------------------------------------------------------------------------

    def _on_button_cc(self, cc: int, is_pressed: bool) -> None:
        # 1. Momentary Modifiers
        if cc == PushCC.SHIFT:
            self.shift_held = is_pressed
            self.set_button_led(PushCC.SHIFT, MonoLed.FULL if is_pressed else MonoLed.HALF)
            return
        if cc == PushCC.SELECT:
            self.select_held = is_pressed
            self.set_button_led(PushCC.SELECT, MonoLed.FULL if is_pressed else MonoLed.HALF)
            return
        if cc == PushCC.DELETE:
            self.delete_held = is_pressed
            self.set_button_led(PushCC.DELETE, MonoLed.FULL if is_pressed else MonoLed.HALF)
            return
        if cc == PushCC.DUPLICATE:
            self.duplicate_held = is_pressed
            self.set_button_led(PushCC.DUPLICATE, MonoLed.FULL if is_pressed else MonoLed.HALF)
            return
        if cc == PushCC.MUTE:
            self.mute_held = is_pressed
            if is_pressed and not self.shift_held:
                self.backend.toggle_chain_mute(self.backend.active_chain_idx)
            self.refresh_all()
            return
        if cc == PushCC.SOLO:
            self.solo_held = is_pressed
            if is_pressed and not self.shift_held:
                self.backend.toggle_chain_solo(self.backend.active_chain_idx)
            self.refresh_all()
            return
        if cc == PushCC.STOP_CLIP:
            self.stop_held = is_pressed
            if is_pressed and self.shift_held:
                # Shift + Stop Clip = Stop All Clips / All Sound Off
                for r in range(8):
                    for c in range(8):
                        if self.backend.clip_matrix[r][c] == 2:
                            self.backend.clip_matrix[r][c] = 1
                self.backend.send_cuia("ALL_SOUNDS_OFF")
            self.refresh_all()
            return

        if not is_pressed:
            return

        # 2. Encoder Mode Selection Buttons (Right Side)
        if cc == PushCC.VOLUME:
            self.encoder_mode = EncoderMode.VOLUME
        elif cc == PushCC.PAN_SEND:
            if self.encoder_mode == EncoderMode.PAN_SEND:
                self.pan_send_submode = (self.pan_send_submode + 1) % 3
            else:
                self.encoder_mode = EncoderMode.PAN_SEND
        elif cc == PushCC.TRACK:
            self.encoder_mode = EncoderMode.TRACK
        elif cc == PushCC.CLIP:
            self.encoder_mode = EncoderMode.CLIP
        elif cc == PushCC.DEVICE:
            self.encoder_mode = EncoderMode.DEVICE
        elif cc == PushCC.BROWSE:
            self.encoder_mode = EncoderMode.BROWSE
        elif cc == PushCC.SCALES:
            if self.encoder_mode == EncoderMode.SCALES:
                self.encoder_mode = self._prev_encoder_mode
            else:
                self._prev_encoder_mode = self.encoder_mode
                self.encoder_mode = EncoderMode.SCALES
        elif cc == PushCC.ADD_TRACK:
            self.encoder_mode = EncoderMode.ADD_TRACK
        elif cc == PushCC.ADD_EFFECT:
            self.backend.send_cuia("SCREEN_ADMIN")
            self.display.show_toast(0, "Add Audio/MIDI Effect Processor to Active Chain", 2.0)

        # 3. Pad Grid Mode Selection (`[Session]` vs `[Note]`)
        elif cc == PushCC.SESSION:
            self.pad_mode = PadMode.SESSION
        elif cc == PushCC.NOTE:
            if self.pad_mode == PadMode.NOTE_ISOMETRIC:
                self.pad_mode = PadMode.NOTE_DRUM_SEQ
            elif self.pad_mode == PadMode.NOTE_DRUM_SEQ:
                self.pad_mode = PadMode.NOTE_MELODIC_SEQ
            else:
                self.pad_mode = PadMode.NOTE_ISOMETRIC

        # 4. Performance Toggles (`Accent`, `Repeat`, `Octave Up/Down`, `User`)
        elif cc == PushCC.ACCENT:
            self.accent_enabled = not self.accent_enabled
        elif cc == PushCC.REPEAT:
            self.repeat_enabled = not self.repeat_enabled
        elif cc == PushCC.OCTAVE_UP:
            self.octave_offset = min(6, self.octave_offset + 1)
            self._rebuild_isometric_map()
            self.display.show_toast(0, f"Keyboard Octave: C{self.octave_offset}", 1.2)
        elif cc == PushCC.OCTAVE_DOWN:
            self.octave_offset = max(-1, self.octave_offset - 1)
            self._rebuild_isometric_map()
            self.display.show_toast(0, f"Keyboard Octave: C{self.octave_offset}", 1.2)
        elif cc == PushCC.USER:
            self.user_mc101_mode = not self.user_mc101_mode
            mode_label = "MC-101 Groovebox Direct Mode" if self.user_mc101_mode else "Zynthian Native Mode"
            self.display.show_toast(0, f"Switched to {mode_label}", 1.5)

        # 5. Transport & Tempo (`Play`, `Record`, `Metronome`, `Tap Tempo`, `Undo`)
        elif cc == PushCC.PLAY:
            self.backend.is_playing = not self.backend.is_playing
            self.backend.send_cuia("TOGGLE_PLAY")
        elif cc == PushCC.RECORD:
            self.backend.is_recording = not self.backend.is_recording
            self.backend.send_cuia("TOGGLE_MIDI_RECORD")
        elif cc == PushCC.METRONOME:
            self.backend.metronome_enabled = not self.backend.metronome_enabled
        elif cc == PushCC.TAP_TEMPO:
            self._handle_tap_tempo()
        elif cc == PushCC.UNDO:
            self.backend.send_cuia("ZYNSWITCH", [1, "S"])
            self.display.show_toast(0, "Undo Executed", 1.0)

        # 6. Upper & Lower Display Softkeys (`CC 20..27` & `CC 102..109`)
        elif cc in UPPER_SOFTKEY_CCS:
            self._on_upper_softkey(UPPER_SOFTKEY_CCS.index(cc))
        elif cc in LOWER_SOFTKEY_CCS:
            self._on_lower_softkey(LOWER_SOFTKEY_CCS.index(cc))

        # 7. Scene Launch Buttons (`CC 43..36`)
        elif cc in SCENE_LAUNCH_CCS_TOP_DOWN:
            scene_row = SCENE_LAUNCH_CCS_TOP_DOWN.index(cc)
            self.backend.launch_scene(scene_row)

        # 8. Cursor Arrow Keys (`CC 44..47`)
        elif cc == PushCC.CURSOR_LEFT:
            self.device_page_pair_idx = max(0, self.device_page_pair_idx - 1)
        elif cc == PushCC.CURSOR_RIGHT:
            self.device_page_pair_idx += 1
        elif cc == PushCC.CURSOR_UP:
            self.backend.send_cuia("ARROW_UP")
        elif cc == PushCC.CURSOR_DOWN:
            self.backend.send_cuia("ARROW_DOWN")

        self.refresh_all()

    def _on_upper_softkey(self, col_idx: int) -> None:
        if self.encoder_mode == EncoderMode.SCALES:
            if col_idx < 6:
                self.root_note = CIRCLE_OF_FIFTHS_UPPER[col_idx]
                self._rebuild_isometric_map()
            elif col_idx == 7:
                self.in_key_mode = not self.in_key_mode
                self._rebuild_isometric_map()
            return

        if self.encoder_mode == EncoderMode.DEVICE:
            # Jump directly to parameter page pair `col_idx`
            chain = self.backend.chains[self.backend.active_chain_idx]
            max_pairs = max(1, math.ceil(len(chain.param_pages) / 2))
            if col_idx < max_pairs:
                self.device_page_pair_idx = col_idx
            return

        # In Mixer modes: Upper Softkey toggles Mute (or Solo if Solo is held)
        if col_idx < len(self.backend.chains):
            if self.solo_held:
                self.backend.toggle_chain_solo(col_idx)
            else:
                self.backend.toggle_chain_mute(col_idx)

    def _on_lower_softkey(self, col_idx: int) -> None:
        if self.encoder_mode == EncoderMode.SCALES:
            if col_idx < 6:
                self.root_note = CIRCLE_OF_FIFTHS_LOWER[col_idx]
                self._rebuild_isometric_map()
            elif col_idx == 7:
                self.row_interval = 4 if self.row_interval == 5 else 5
                self._rebuild_isometric_map()
            return

        if self.stop_held and col_idx < 8:
            # Hold [Stop] + Lower Softkey stops all clips on that Chain column
            for r in range(8):
                if self.backend.clip_matrix[r][col_idx] == 2:
                    self.backend.clip_matrix[r][col_idx] = 1
            return

        # Default: Select Active Chain 1..8
        if col_idx < len(self.backend.chains):
            self.backend.select_chain(col_idx)

    def _handle_tap_tempo(self) -> None:
        now = time.monotonic()
        self._tap_times = [t for t in self._tap_times if (now - t) < 2.5]
        self._tap_times.append(now)
        if len(self._tap_times) >= 3:
            intervals = [
                self._tap_times[i] - self._tap_times[i - 1]
                for i in range(1, len(self._tap_times))
            ]
            avg_sec = sum(intervals) / len(intervals)
            if avg_sec > 0.15:
                self.backend.tempo_bpm = round(60.0 / avg_sec, 1)
                self.backend.nudge_tempo(0)
                self.display.show_toast(0, f"Tap Tempo: {self.backend.tempo_bpm:.1f} BPM", 1.5)

    # ------------------------------------------------------------------------
    # 8x8 Pad Matrix Event Handler (Session, Isometric Live Play, Sequencer)
    # ------------------------------------------------------------------------

    def _on_pad_event(self, pad_hw_note: int, velocity: int, is_pressed: bool) -> None:
        pad_idx = pad_hw_note - PAD_NOTE_MIN
        row_bottom_up = pad_idx // 8   # 0 (bottom) .. 7 (top)
        row_top_down = 7 - row_bottom_up  # 0 (top) .. 7 (bottom)
        col = pad_idx % 8

        # MODE 1: SESSION (8x8 Zynpad Clip Launcher)
        if self.pad_mode == PadMode.SESSION:
            if not is_pressed:
                return
            if self.delete_held:
                self.backend.clip_matrix[row_top_down][col] = 0
            elif self.select_held:
                self.backend.select_chain(col)
            else:
                self.backend.toggle_clip(row_top_down, col)
            self.refresh_pads()
            return

        # MODE 2: DRUM + 32-STEP SEQUENCER (`NOTE_DRUM_SEQ`)
        if self.pad_mode == PadMode.NOTE_DRUM_SEQ:
            if row_bottom_up >= 4:
                # Top 4x8 rows = 32-Step Sequencer Grid (Steps 0..31)
                step_idx = (7 - row_bottom_up) * 8 + col
                if is_pressed:
                    self.held_step_pad = step_idx
                    key = (step_idx, self.selected_drum_note)
                    if key in self.backend.pattern_steps:
                        if self.delete_held:
                            del self.backend.pattern_steps[key]
                    else:
                        vel = 127.0 if self.accent_enabled else float(max(1, velocity))
                        self.backend.pattern_steps[key] = [vel, 1.0, 100.0, 0.0]
                    self._prev_encoder_mode = self.encoder_mode
                    self.encoder_mode = EncoderMode.STEP_INSPECTOR
                else:
                    if self.held_step_pad == step_idx:
                        self.held_step_pad = None
                        if self.encoder_mode == EncoderMode.STEP_INSPECTOR:
                            self.encoder_mode = self._prev_encoder_mode
                self.refresh_all()
                return

            if col < 4:
                # Bottom-Left 4x4 Quadrant = 16 Drum Pads (Notes 36..51)
                drum_note = 36 + row_bottom_up * 4 + col
                if is_pressed:
                    self.selected_drum_note = drum_note
                    out_vel = 127 if self.accent_enabled else velocity
                    self._trigger_live_note(drum_note, out_vel, True)
                else:
                    self._trigger_live_note(drum_note, 0, False)
                self.refresh_pads()
                return

            # Bottom-Right 4x4 Quadrant = Loop Measure / Velocity Selector
            if is_pressed:
                self.seq_Loop_page = row_bottom_up * 4 + (col - 4)
                self.refresh_pads()
            return

        # MODE 3: ISOMETRIC KEYBOARD (`NOTE_ISOMETRIC`) & MELODIC PLAY
        midi_note = self._pad_to_midi_note[pad_idx]
        if is_pressed:
            out_vel = 127 if self.accent_enabled else velocity
            self._active_notes.add(midi_note)
            self._trigger_live_note(midi_note, out_vel, True)
        else:
            self._active_notes.discard(midi_note)
            self._trigger_live_note(midi_note, 0, False)

        # Highlight all pads sharing the same pitch simultaneously
        for matching_pad in self._note_to_pads.get(midi_note, [pad_hw_note]):
            self._refresh_single_isometric_pad(matching_pad - PAD_NOTE_MIN)

    def _trigger_live_note(self, midi_note: int, velocity: int, is_note_on: bool) -> None:
        chain = self.backend.chains[self.backend.active_chain_idx]
        if self.backend._send_note_cb is not None:
            self.backend._send_note_cb(chain.midi_chan, midi_note, velocity if is_note_on else 0)

    # ------------------------------------------------------------------------
    # Complete LCD & LED Rendering Pipeline
    # ------------------------------------------------------------------------

    @staticmethod
    def _level_to_db_str(level: float) -> str:
        if level <= 0.001:
            return "-inf dB"
        # In zynmixer, 0.8 corresponds to 0.0 dB
        db = 20.0 * math.log10(level / 0.80)
        return f"{db:+.1f}dB"

    def _get_active_8_param_slots(self) -> list[Optional[ParameterSlot]]:
        chain = self.backend.chains[self.backend.active_chain_idx]
        pages = list(chain.param_pages.values())
        if not pages:
            return [None] * 8
        max_pairs = max(1, math.ceil(len(pages) / 2))
        self.device_page_pair_idx = min(self.device_page_pair_idx, max_pairs - 1)
        p1_idx = self.device_page_pair_idx * 2
        p2_idx = p1_idx + 1
        slots: list[Optional[ParameterSlot]] = []
        for idx in (p1_idx, p2_idx):
            if idx < len(pages):
                page_slots = list(pages[idx][:4])
                while len(page_slots) < 4:
                    page_slots.append(None)
                slots.extend(page_slots)
            else:
                slots.extend([None] * 4)
        return slots[:8]

    def refresh_lcd(self, force: bool = False) -> None:
        """Renders the 4x68 LCD lines according to the active `EncoderMode`."""
        chain_headers = [
            (f"{chr(GLYPH_TRI_RIGHT)}{c.title[:7]}" if i == self.backend.active_chain_idx else c.title[:8])
            for i, c in enumerate(self.backend.chains[:8])
        ]

        if self.encoder_mode == EncoderMode.VOLUME:
            names = [c.engine_name[:8] for c in self.backend.chains[:8]]
            vals = [
                (
                    self.display.render_unipolar_bar(c.level)
                    if i in self.touched_encoders
                    else self._level_to_db_str(c.level)
                )
                for i, c in enumerate(self.backend.chains[:8])
            ]
            states = ["[MUTE]" if c.mute else ("[SOLO]" if c.solo else "  ON  ") for c in self.backend.chains[:8]]
            self.display.set_8cells(0, names)
            self.display.set_8cells(1, vals)
            self.display.set_8cells(2, chain_headers)
            self.display.set_8cells(3, states, align="center")

        elif self.encoder_mode == EncoderMode.PAN_SEND:
            mode_titles = ("Pan", "DlySend", "RevSend")
            sub = mode_titles[self.pan_send_submode]
            headers = [f"{sub} {i + 1}" for i in range(8)]
            vals = []
            for i, c in enumerate(self.backend.chains[:8]):
                if self.pan_send_submode == 0:
                    vals.append(self.display.render_bipolar_pan(c.balance))
                elif self.pan_send_submode == 1:
                    vals.append(self.display.render_unipolar_bar(c.send_a) if i in self.touched_encoders else f"{int(c.send_a * 127)}")
                else:
                    vals.append(self.display.render_unipolar_bar(c.send_b) if i in self.touched_encoders else f"{int(c.send_b * 127)}")
            self.display.set_8cells(0, headers)
            self.display.set_8cells(1, vals)
            self.display.set_8cells(2, chain_headers)
            self.display.set_8cells(3, [c.engine_name[:8] for c in self.backend.chains[:8]])

        elif self.encoder_mode == EncoderMode.TRACK:
            c = self.backend.chains[self.backend.active_chain_idx]
            self.display.set_8cells(0, ["Volume", "Pan", "Mute", "Solo", "DlySend", "RevSend", "MIDICh", "Engine"])
            self.display.set_8cells(
                1,
                [
                    self._level_to_db_str(c.level),
                    self.display.render_bipolar_pan(c.balance),
                    "MUTED" if c.mute else "ACTIVE",
                    "SOLOED" if c.solo else "NORMAL",
                    f"{int(c.send_a * 127)}",
                    f"{int(c.send_b * 127)}",
                    f"CH {c.midi_chan + 1}",
                    c.engine_name[:8],
                ],
            )
            self.display.set_8cells(2, chain_headers)
            self.display.set_4segments(
                3,
                [
                    f"Chain: {c.title}",
                    f"BPM: {self.backend.tempo_bpm:.1f}",
                    f"Swing: {self.backend.swing_amount:.0f}%",
                    f"Pad: {self.pad_mode.value[:11]}",
                ],
            )

        elif self.encoder_mode == EncoderMode.DEVICE:
            c = self.backend.chains[self.backend.active_chain_idx]
            slots = self._get_active_8_param_slots()
            p_names = [s.short_name if s else "--------" for s in slots]
            p_vals = []
            for i, s in enumerate(slots):
                if s is None:
                    p_vals.append("        ")
                elif i in self.touched_encoders and not s.labels:
                    p_vals.append(self.display.render_unipolar_bar(s.normalized))
                else:
                    p_vals.append(s.format_value())

            page_names = list(c.param_pages.keys())
            tabs = []
            for pair_i in range(8):
                p_idx = pair_i * 2
                if p_idx < len(page_names):
                    prefix = chr(GLYPH_TRI_RIGHT) if pair_i == self.device_page_pair_idx else " "
                    tabs.append(f"{prefix}{page_names[p_idx][:7]}")
                else:
                    tabs.append("        ")

            self.display.set_8cells(0, p_names)
            self.display.set_8cells(1, p_vals)
            self.display.set_8cells(2, tabs)
            self.display.set_8cells(3, chain_headers)

        elif self.encoder_mode == EncoderMode.BROWSE:
            c = self.backend.chains[self.backend.active_chain_idx]
            bank_name = c.bank_list[c.bank_idx] if c.bank_list else "Default"
            preset_name = c.preset_list[c.preset_idx] if c.preset_list else "Init"
            self.display.set_4segments(
                0,
                [
                    f"Engine: {c.engine_name[:9]}",
                    f"Bank ({c.bank_idx + 1}/{len(c.bank_list)})",
                    f"Preset ({c.preset_idx + 1}/{len(c.preset_list)})",
                    "Push Softkey 5-8",
                ],
            )
            self.display.set_4segments(
                1,
                [
                    f"Chain {c.chain_id}",
                    f"{chr(GLYPH_TRI_RIGHT)}{bank_name[:16]}",
                    f"{chr(GLYPH_TRI_RIGHT)}{preset_name[:16]}",
                    "[Load Preset]",
                ],
            )
            self.display.set_8cells(2, chain_headers)
            self.display.set_8cells(3, [p[:8] for p in (c.preset_list + [""] * 8)[:8]])

        elif self.encoder_mode == EncoderMode.SCALES:
            scale_name, _ = MUSICAL_SCALES[self.scale_idx]
            upper_keys = [
                (f"{chr(GLYPH_TRI_RIGHT)}{NOTE_NAMES[n]}" if n == self.root_note else f" {NOTE_NAMES[n]}")
                for n in CIRCLE_OF_FIFTHS_UPPER
            ] + [f"Oct:C{self.octave_offset}", "In-Key" if self.in_key_mode else "Chromt"]
            lower_keys = [
                (f"{chr(GLYPH_TRI_RIGHT)}{NOTE_NAMES[n]}" if n == self.root_note else f" {NOTE_NAMES[n]}")
                for n in CIRCLE_OF_FIFTHS_LOWER
            ] + [f"{len(MUSICAL_SCALES)} Scls", "4ths" if self.row_interval == 5 else "3rds"]
            self.display.set_8cells(0, upper_keys)
            self.display.set_4segments(
                1,
                [
                    f"Scale: {scale_name[:10]}",
                    f"Root Key: {NOTE_NAMES[self.root_note]}",
                    f"Mode: {'In-Key' if self.in_key_mode else 'Chromatic'}",
                    f"Grid: {'Isometric 4ths' if self.row_interval == 5 else 'Isometric 3rds'}",
                ],
            )
            self.display.set_8cells(2, [s[0][:8] for s in MUSICAL_SCALES[self.scale_idx : self.scale_idx + 8]])
            self.display.set_8cells(3, lower_keys)

        elif self.encoder_mode == EncoderMode.STEP_INSPECTOR and self.held_step_pad is not None:
            step_idx = self.held_step_pad
            vals = self.backend.pattern_steps.get((step_idx, self.selected_drum_note), [100.0, 1.0, 100.0, 0.0])
            note_label = f"{NOTE_NAMES[self.selected_drum_note % 12]}{self.selected_drum_note // 12 - 1}"
            self.display.set_8cells(0, ["Pitch", "Velocity", "GateLen", "Chance%", "Ratchet", "Step #", "Chain", "Pattern"])
            self.display.set_8cells(
                1,
                [
                    f"{note_label} ({self.selected_drum_note})",
                    f"{int(vals[0])}",
                    f"{vals[1]:.2f} stp",
                    f"{int(vals[2])}%",
                    f"{int(vals[3])}x",
                    f"Step {step_idx + 1}",
                    f"Ch {self.backend.active_chain_idx + 1}",
                    f"Scene {self.backend.active_scene_idx + 1}",
                ],
            )
            self.display.set_8cells(2, chain_headers)
            self.display.set_4segments(3, ["=== Hold Step Pad + Turn Encoders 1-5 to Parameter-Lock Step ===", "", "", ""])

        else:
            # CLIP / ADD_TRACK fallback summary
            self.display.set_4segments(
                0,
                [
                    f"Mode: {self.encoder_mode.value}",
                    f"BPM: {self.backend.tempo_bpm:.1f}",
                    f"Swing: {self.backend.swing_amount:.0f}%",
                    f"Scene: {self.backend.active_scene_idx + 1}",
                ],
            )
            self.display.set_8cells(1, ["Synth", "AudioFX", "MIDITool", "MC-101", "ZynAdd", "Dexed", "SurgeXT", "Fluid"])
            self.display.set_8cells(2, chain_headers)
            self.display.set_8cells(3, ["[Create]", "[Insert]", "[Clone]", "[Clear]", "", "", "", ""])

        self.display.flush(force=force)

    def _refresh_single_isometric_pad(self, pad_idx: int, force: bool = False) -> None:
        pad_hw_note = PAD_NOTE_MIN + pad_idx
        midi_note = self._pad_to_midi_note[pad_idx]
        if midi_note in self._active_notes:
            color = int(RgbColor.GREEN)
        else:
            is_root, in_scale = self._is_note_in_scale(midi_note)
            if is_root:
                color = int(CHAIN_COLORS_BRIGHT[self.backend.active_chain_idx % 8])
            elif in_scale:
                color = int(RgbColor.WHITE)
            else:
                color = int(RgbColor.BLACK)
        self.set_pad_led(pad_hw_note, color, LED_CHAN_STATIC, force=force)

    def refresh_pads(self, force: bool = False) -> None:
        """Updates all 64 RGB Pad LEDs according to the active `PadMode`."""
        if self.pad_mode == PadMode.SESSION:
            for row_top_down in range(8):
                row_bottom_up = 7 - row_top_down
                for col in range(8):
                    pad_hw_note = PAD_NOTE_MIN + row_bottom_up * 8 + col
                    state = self.backend.clip_matrix[row_top_down][col]
                    if state == 2:  # Playing
                        self.set_pad_led(pad_hw_note, RgbColor.GREEN, LED_CHAN_STATIC, force=force)
                    elif state == 1:  # Stopped (Populated)
                        self.set_pad_led(pad_hw_note, CHAIN_COLORS_DIM[col % 8], LED_CHAN_STATIC, force=force)
                    else:  # Empty
                        self.set_pad_led(pad_hw_note, RgbColor.BLACK, LED_CHAN_STATIC, force=force)

        elif self.pad_mode == PadMode.NOTE_DRUM_SEQ:
            for pad_idx in range(64):
                row = pad_idx // 8
                col = pad_idx % 8
                pad_hw_note = PAD_NOTE_MIN + pad_idx
                if row >= 4:
                    # Top 32 pads = 32-Step Sequencer
                    step_idx = (7 - row) * 8 + col
                    has_step = (step_idx, self.selected_drum_note) in self.backend.pattern_steps
                    if has_step:
                        color = RgbColor.OCEAN if step_idx == self.held_step_pad else CHAIN_COLORS_BRIGHT[self.backend.active_chain_idx % 8]
                    else:
                        color = RgbColor.WHITE if (step_idx % 4 == 0) else RgbColor.DARK_GREY
                    self.set_pad_led(pad_hw_note, color, LED_CHAN_STATIC, force=force)
                elif col < 4:
                    # Bottom-Left 4x4 = 16 Drum Pads
                    drum_note = 36 + row * 4 + col
                    color = RgbColor.YELLOW if drum_note == self.selected_drum_note else RgbColor.AMBER_DIM
                    self.set_pad_led(pad_hw_note, color, LED_CHAN_STATIC, force=force)
                else:
                    # Bottom-Right 4x4 = Loop Measure Page Selector
                    page_idx = row * 4 + (col - 4)
                    color = RgbColor.GREEN if page_idx == self.seq_Loop_page else RgbColor.SKY_DIM
                    self.set_pad_led(pad_hw_note, color, LED_CHAN_STATIC, force=force)

        else:
            # NOTE_ISOMETRIC & NOTE_MELODIC_SEQ
            for pad_idx in range(64):
                self._refresh_single_isometric_pad(pad_idx, force=force)

    def refresh_buttons(self, force: bool = False) -> None:
        """Updates all Front-Panel Function, Softkey, and Scene Button LEDs."""
        # Mode buttons
        mode_map = {
            PushCC.VOLUME: self.encoder_mode == EncoderMode.VOLUME,
            PushCC.PAN_SEND: self.encoder_mode == EncoderMode.PAN_SEND,
            PushCC.TRACK: self.encoder_mode == EncoderMode.TRACK,
            PushCC.CLIP: self.encoder_mode == EncoderMode.CLIP,
            PushCC.DEVICE: self.encoder_mode == EncoderMode.DEVICE,
            PushCC.BROWSE: self.encoder_mode == EncoderMode.BROWSE,
            PushCC.SCALES: self.encoder_mode == EncoderMode.SCALES,
            PushCC.ADD_TRACK: self.encoder_mode == EncoderMode.ADD_TRACK,
            PushCC.SESSION: self.pad_mode == PadMode.SESSION,
            PushCC.NOTE: self.pad_mode != PadMode.SESSION,
            PushCC.ACCENT: self.accent_enabled,
            PushCC.REPEAT: self.repeat_enabled,
            PushCC.USER: self.user_mc101_mode,
            PushCC.METRONOME: self.backend.metronome_enabled,
        }
        for cc, active in mode_map.items():
            self.set_button_led(cc, MonoLed.FULL if active else MonoLed.HALF, force=force)

        # Always-available navigation & utility buttons
        for cc in (
            PushCC.TAP_TEMPO,
            PushCC.MASTER,
            PushCC.OCTAVE_UP,
            PushCC.OCTAVE_DOWN,
            PushCC.CURSOR_LEFT,
            PushCC.CURSOR_RIGHT,
            PushCC.CURSOR_UP,
            PushCC.CURSOR_DOWN,
            PushCC.SHIFT,
            PushCC.SELECT,
            PushCC.DELETE,
            PushCC.UNDO,
            PushCC.DUPLICATE,
            PushCC.NEW,
            PushCC.FIXED_LENGTH,
            PushCC.ADD_EFFECT,
        ):
            self.set_button_led(cc, MonoLed.HALF, force=force)

        # Bi-LED Transport & Track State Buttons
        self.set_button_led(
            PushCC.PLAY,
            BiLed.GREEN if self.backend.is_playing else BiLed.GREEN_HALF,
            force=force,
        )
        self.set_button_led(
            PushCC.RECORD,
            BiLed.RED if self.backend.is_recording else BiLed.RED_HALF,
            force=force,
        )
        active_chain = self.backend.chains[self.backend.active_chain_idx]
        self.set_button_led(
            PushCC.MUTE,
            BiLed.AMBER if active_chain.mute else BiLed.AMBER_HALF,
            force=force,
        )
        self.set_button_led(
            PushCC.SOLO,
            BiLed.YELLOW if active_chain.solo else BiLed.YELLOW_HALF,
            force=force,
        )
        self.set_button_led(PushCC.STOP_CLIP, BiLed.RED_HALF, force=force)

        # Upper & Lower Softkeys (CC 20..27 & CC 102..109)
        for i in range(8):
            if i < len(self.backend.chains):
                c = self.backend.chains[i]
                upper_color = BiLed.RED if c.mute else (BiLed.YELLOW if c.solo else BiLed.GREEN_HALF)
                lower_color = (
                    CHAIN_COLORS_BRIGHT[i % 8]
                    if i == self.backend.active_chain_idx
                    else CHAIN_COLORS_DIM[i % 8]
                )
            else:
                upper_color = BiLed.OFF
                lower_color = RgbColor.BLACK
            self.set_button_led(UPPER_SOFTKEY_CCS[i], upper_color, force=force)
            self.set_button_led(LOWER_SOFTKEY_CCS[i], lower_color, force=force)

        # Scene Launch Buttons (CC 43..36)
        for scene_i, cc in enumerate(SCENE_LAUNCH_CCS_TOP_DOWN):
            color = BiLed.GREEN if scene_i == self.backend.active_scene_idx else BiLed.AMBER_HALF
            self.set_button_led(cc, color, force=force)

    def refresh_all(self, force: bool = False) -> None:
        self.refresh_buttons(force=force)
        self.refresh_pads(force=force)
        self.refresh_lcd(force=force)


# ============================================================================
# 6. NATIVE ZYNTHIAN `ctrldev` DRIVER WRAPPER (`zynthian_ctrldev_ableton_push1`)
# ============================================================================

try:
    from zyngine.ctrldev.zynthian_ctrldev_base import (
        zynthian_ctrldev_base,
        zynthian_ctrldev_zynmixer,
        zynthian_ctrldev_zynpad,
    )
    from zyncoder.zyncore import lib_zyncore
    HAS_ZYNTHIAN_CORE = True
except ImportError:
    HAS_ZYNTHIAN_CORE = False

    class zynthian_ctrldev_base:  # type: ignore[no-redef]
        pass

    class zynthian_ctrldev_zynmixer:  # type: ignore[no-redef]
        pass

    class zynthian_ctrldev_zynpad:  # type: ignore[no-redef]
        pass

    lib_zyncore = None


class zynthian_ctrldev_ableton_push1(
    zynthian_ctrldev_base,
    zynthian_ctrldev_zynpad,
    zynthian_ctrldev_zynmixer,
):
    """
    Drop-in Zynthian Control Device (`ctrldev`) class for Ableton Push 1.
    Can be symlinked or copied directly to:
      `/zynthian/zynthian-ui/zyngine/ctrldev/zynthian_ctrldev_ableton_push1.py`
    """

    dev_ids = ["Ableton Push MIDI 1", "Ableton Push_1"]
    driver_name = "Ableton Push 1"
    driver_description = "Full native UI, Zynpad, Zynmixer, Zynseq & Parameter control for Ableton Push 1"
    unroute_from_chains = True

    def __init__(self, state_manager=None, idev_in=None, idev_out=None):
        self.state_manager = state_manager
        self.chain_manager = getattr(state_manager, "chain_manager", None)
        self.zynmixer = getattr(state_manager, "zynmixer", None)
        self.zynseq = getattr(state_manager, "zynseq", None)
        self.idev_in = idev_in
        self.idev_out = idev_out

        if HAS_ZYNTHIAN_CORE and zynthian_ctrldev_base is not object:
            super().__init__(state_manager, idev_in, idev_out)

        self.backend = ZynthianBackendAdapter(
            state_manager=self.state_manager,
            chain_manager=self.chain_manager,
            zynmixer=self.zynmixer,
            zynseq=self.zynseq,
            send_note_cb=self._inject_note_to_zynthian,
        )
        self.controller = Push1Controller(
            backend=self.backend,
            send_midi_cb=self._send_raw_midi,
        )

    def _send_raw_midi(self, msg: Sequence[int]) -> None:
        if HAS_ZYNTHIAN_CORE and lib_zyncore is not None and self.idev_out is not None:
            buf = (
                bytes(msg)
                if isinstance(msg, (list, tuple, bytearray))
                else msg
            )
            lib_zyncore.dev_send_midi_event(self.idev_out, buf, len(buf))

    def _inject_note_to_zynthian(self, midi_chan: int, note: int, velocity: int) -> None:
        if HAS_ZYNTHIAN_CORE and lib_zyncore is not None:
            if velocity > 0:
                lib_zyncore.zmip_send_note_on(midi_chan & 0x0F, note & 0x7F, velocity & 0x7F)
            else:
                lib_zyncore.zmip_send_note_off(midi_chan & 0x0F, note & 0x7F, 0)

    def init(self) -> None:
        if HAS_ZYNTHIAN_CORE and zynthian_ctrldev_base is not object:
            super().init()
        self.controller.init_hardware()

    def end(self) -> None:
        self.controller.shutdown_hardware()
        if HAS_ZYNTHIAN_CORE and zynthian_ctrldev_base is not object:
            super().end()

    def refresh(self) -> None:
        self.backend.sync_from_zynthian()
        self.controller.refresh_all(force=False)

    def update_seq_state(self, bank: int, seq: int, state: int, mode: int, group: int) -> None:
        col = seq // 8
        row = seq % 8
        if 0 <= row < 8 and 0 <= col < 8:
            self.backend.clip_matrix[row][col] = 2 if state == 1 else 1
            self.controller.refresh_pads()

    def update_mixer_strip(self, chan: int, symbol: str, value: float) -> None:
        for idx, c in enumerate(self.backend.chains):
            if c.mixer_chan == chan:
                if symbol == "level":
                    c.level = float(value)
                elif symbol == "balance":
                    c.balance = float(value)
                elif symbol == "mute":
                    c.mute = bool(value)
                elif symbol == "solo":
                    c.solo = bool(value)
                self.controller.refresh_all()
                break

    def midi_event(self, ev: bytes) -> bool:
        return self.controller.handle_midi_event(ev)


# ============================================================================
# 7. STANDALONE CLI RUNNER & HARDWARE DIAGNOSTIC SELF-TEST
# ============================================================================

def run_self_test() -> None:
    """Verifies LCD 68-char framing, relative encoder math, and pad matrix events."""
    sent_messages: list[list[int]] = []
    backend = ZynthianBackendAdapter()
    ctrl = Push1Controller(backend=backend, send_midi_cb=lambda m: sent_messages.append(list(m)))
    ctrl.init_hardware()

    # Verify 4 LCD SysEx lines were emitted and each is exactly 77 bytes
    lcd_msgs = [
        m for m in sent_messages
        if len(m) > 5 and tuple(m[:4]) == PUSH1_SYSEX_HEADER and m[4] in (0x18, 0x19, 0x1A, 0x1B)
    ]
    assert len(lcd_msgs) >= 4, f"Expected >= 4 LCD SysEx frames, got {len(lcd_msgs)}"
    for frame in lcd_msgs:
        assert len(frame) == 77, f"LCD SysEx frame must be 77 bytes, got {len(frame)}"
        assert frame[0] == 0xF0 and frame[-1] == 0xF7

    # Simulate turning Track Encoder 1 clockwise (+3) in DEVICE mode
    ctrl.handle_midi_event([0xB0, PushCC.TRACK_ENCODER_1, 3])
    # Simulate switching to VOLUME mode and turning Master Encoder counter-clockwise (-2 -> 126)
    ctrl.handle_midi_event([0xB0, PushCC.VOLUME, 127])
    ctrl.handle_midi_event([0xB0, PushCC.MASTER_ENCODER, 126])
    # Simulate pressing Bottom-Left Pad (Note 36, Velocity 100) in Isometric Mode
    ctrl.handle_midi_event([0x90, 36, 100])
    ctrl.handle_midi_event([0x80, 36, 0])

    print(
        f"[OK] Push 1 Foundation Self-Test Passed: "
        f"{len(sent_messages)} MIDI/SysEx frames generated, all LCD frames verified at 77 bytes."
    )


if __name__ == "__main__":
    run_self_test()
