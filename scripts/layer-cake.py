#!/usr/bin/env python3
# ==============================================================================
# layer-cake.py: SayoDevice 12-Key Virtual Layer Manager & OSD Daemon
# ==============================================================================
# Intercepts SayoDevice physical keystrokes and provides 8 directly selectable
# software layers. Holding Shift and pressing a key jumps straight to a layer:
#
#   Shift + Up    -> Layer 1        Shift + A -> Layer 5
#   Shift + Down  -> Layer 2        Shift + B -> Layer 6
#   Shift + Left  -> Layer 3        Shift + C -> Layer 7
#   Shift + Right -> Layer 4        Shift + D -> Layer 8
#
# Arrow keys always pass through unchanged. Physical keys A, B, C, D are
# translated to the keys defined for the active layer. A single-line overlay
# covering Zynthian's title bar shows the active layer when Shift is pressed
# or when the layer changes.
# ==============================================================================

import argparse
import logging
import os
import queue
import re
import select
import sys
import threading
import time
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [LayerCake] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LayerCake")

# ==============================================================================
# Layer Configuration (edit here)
# ==============================================================================
# 'keys'   : what each physical key (a, b, c, d) emits on this layer
# 'labels' : short description shown on the overlay
# Layers are listed in order: index 0 = Layer 1 ... index 7 = Layer 8.
# ==============================================================================

LAYERS: List[Dict] = [
    {   # Layer 1 (Shift + Up)
        "keys": {"a": "a", "b": "b", "c": "c", "d": "d"},
        "labels": {"a": "Knob 2", "b": "Knob 4", "c": "Btn C1", "d": "Btn D1"},
    },
    {   # Layer 2 (Shift + Down)
        "keys": {"a": "a", "b": "b", "c": "e", "d": "f"},
        "labels": {"a": "Knob 2", "b": "Knob 4", "c": "Btn C2", "d": "Btn D2"},
    },
    {   # Layer 3 (Shift + Left)
        "keys": {"a": "a", "b": "b", "c": "g", "d": "h"},
        "labels": {"a": "Knob 2", "b": "Knob 4", "c": "Btn C3", "d": "Btn D3"},
    },
    {   # Layer 4 (Shift + Right)
        "keys": {"a": "a", "b": "b", "c": "i", "d": "j"},
        "labels": {"a": "Knob 2", "b": "Knob 4", "c": "Btn C4", "d": "Btn D4"},
    },
    {   # Layer 5 (Shift + A)
        "keys": {"a": "a", "b": "b", "c": "k", "d": "l"},
        "labels": {"a": "Knob 2", "b": "Knob 4", "c": "Btn C5", "d": "Btn D5"},
    },
    {   # Layer 6 (Shift + B)
        "keys": {"a": "a", "b": "b", "c": "m", "d": "n"},
        "labels": {"a": "Knob 2", "b": "Knob 4", "c": "Btn C6", "d": "Btn D6"},
    },
    {   # Layer 7 (Shift + C) - secondary / parameter editing
        "keys": {"a": "o", "b": "p", "c": "q", "d": "r"},
        "labels": {"a": "Edit A7", "b": "Edit B7", "c": "Edit C7", "d": "Edit D7"},
    },
    {   # Layer 8 (Shift + D) - secondary / parameter editing
        "keys": {"a": "s", "b": "t", "c": "u", "d": "v"},
        "labels": {"a": "Edit A8", "b": "Edit B8", "c": "Edit C8", "d": "Edit D8"},
    },
]

# Physical key (evdev name) used together with Shift to select each layer
LAYER_SELECT_KEYS: List[str] = [
    "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT",
    "KEY_A", "KEY_B", "KEY_C", "KEY_D",
]

# Physical action keys and their logical names
ACTION_KEYS: Dict[str, str] = {"KEY_A": "a", "KEY_B": "b", "KEY_C": "c", "KEY_D": "d"}

# ==============================================================================
# Overlay appearance
# ==============================================================================
# Font family and size are read from Zynthian's config so the overlay matches
# the native title bar. Set OVERLAY_HEIGHT / OVERLAY_FONT_SIZE to a number to
# override the automatic values.
# ==============================================================================

ZYNTHIAN_ENVARS_FILE = "/zynthian/config/zynthian_envars.sh"
OVERLAY_HEIGHT: Optional[int] = None      # None = same as Zynthian topbar height
OVERLAY_FONT_SIZE: Optional[int] = 16     # None = same as Zynthian topbar font size
OVERLAY_TEXT_Y_OFFSET = -4                # Vertical pixel nudge (negative moves text up)
OVERLAY_DURATION_MS = 1800
OVERLAY_FG = "#ffffff"
OVERLAY_BG = "#000000"


def read_zynthian_envar(name: str, default: str) -> str:
    """Return a Zynthian UI setting from the environment or zynthian_envars.sh."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        with open(ZYNTHIAN_ENVARS_FILE, "r") as fh:
            for line in fh:
                m = re.match(rf'^\s*export\s+{name}\s*=\s*["\']?([^"\'\n#]*)', line)
                if m and m.group(1).strip():
                    return m.group(1).strip()
    except OSError:
        pass
    return default


def format_layer_line(layer_idx: int, layer: Dict) -> str:
    """Build the single overlay line, e.g. '1:   [A] Knob 2   |   [B] Knob 4   |   ...'."""
    labels = layer.get("labels", {})
    parts = []
    for k in ("a", "b", "c", "d"):
        label = labels.get(k, layer["keys"].get(k, k).upper())
        parts.append(f"[{k.upper()}] {label}")
    return f"{layer_idx + 1}:   " + "   |   ".join(parts)


# ==============================================================================
# Title Bar Overlay (Tkinter on DISPLAY=:0)
# ==============================================================================

class TitleBarOverlay:
    """Single-line overlay drawn over Zynthian's title bar."""

    def __init__(self, display_str: str = ":0") -> None:
        self.enabled = False
        self.root = None
        self.label = None
        self.hide_timer_id = None
        self.event_queue: queue.Queue = queue.Queue()

        if not display_str:
            return
        os.environ["DISPLAY"] = display_str

        try:
            import tkinter as tk
            self.tk = tk
        except ImportError:
            logger.warning("python3-tk is not installed. Overlay disabled.")
            return

        # Wait for X11 to come up when started at boot
        for attempt in range(20):
            try:
                self.root = tk.Tk()
                break
            except Exception as exc:
                if attempt == 19:
                    logger.warning("Display %s not available (%s). Overlay disabled.", display_str, exc)
                    return
                time.sleep(1.0)

        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()

            # Same topbar geometry/font rules as zyngui/zynthian_gui_config.py
            font_family = read_zynthian_envar("ZYNTHIAN_UI_FONT_FAMILY", "Audiowide")
            try:
                ui_font_size = int(read_zynthian_envar("ZYNTHIAN_UI_FONT_SIZE", "16"))
            except ValueError:
                ui_font_size = 16
            if not ui_font_size:
                ui_font_size = int(screen_w / 40)
            if screen_w >= 800:
                topbar_height = screen_h // 12
                topbar_fs = int(1.5 * ui_font_size)
            else:
                topbar_height = screen_h // 10
                topbar_fs = int(1.1 * ui_font_size)

            font_size = OVERLAY_FONT_SIZE or topbar_fs
            height = OVERLAY_HEIGHT or topbar_height

            self.root.title("LayerCakeOverlay")
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.configure(bg=OVERLAY_BG)
            self.root.geometry(f"{screen_w}x{height}+0+0")

            self.label = tk.Label(
                self.root,
                text="",
                font=(font_family, font_size),
                fg=OVERLAY_FG,
                bg=OVERLAY_BG,
                anchor="w",
                padx=0,
                pady=0,
                borderwidth=0,
                highlightthickness=0,
            )
            self.label.place(x=10, rely=0.5, y=OVERLAY_TEXT_Y_OFFSET, anchor="w")

            self.root.withdraw()
            self.enabled = True
            logger.info("Overlay ready on %s (%dx%d, font '%s' %d)",
                        display_str, screen_w, height, font_family, font_size)
        except Exception as exc:
            logger.warning("Could not configure overlay (%s). Overlay disabled.", exc)
            self.enabled = False

    def notify_layer(self, layer_idx: int, layer: Dict) -> None:
        self.event_queue.put((layer_idx, layer))

    def _show(self, layer_idx: int, layer: Dict) -> None:
        self.label.config(text=format_layer_line(layer_idx, layer))
        if self.hide_timer_id is not None:
            self.root.after_cancel(self.hide_timer_id)
        self.root.deiconify()
        self.root.lift()
        self.hide_timer_id = self.root.after(OVERLAY_DURATION_MS, self._hide)

    def _hide(self) -> None:
        self.root.withdraw()
        self.hide_timer_id = None

    def run_loop(self) -> None:
        def process_queue():
            try:
                while True:
                    layer_idx, layer = self.event_queue.get_nowait()
                    self._show(layer_idx, layer)
            except queue.Empty:
                pass
            self.root.after(30, process_queue)

        self.root.after(30, process_queue)
        self.root.mainloop()


# ==============================================================================
# Key Interceptor & Virtual Keyboard
# ==============================================================================

class LayerManager:
    """Grabs SayoDevice events and re-emits translated keys via uinput."""

    def __init__(self, layers: List[Dict], overlay: TitleBarOverlay, device_query: str = "SayoDevice") -> None:
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            logger.error("python3-evdev is not installed. Run: apt-get install -y python3-evdev")
            sys.exit(1)

        self.evdev = evdev
        self.ecodes = ecodes
        self.layers = layers
        self.overlay = overlay
        self.device_query = device_query.lower()
        self.current_layer = 0
        self.shift_held = False
        self.devices: List = []
        self.uinput = None

        self.shift_codes = {ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT}
        self.layer_select = {getattr(ecodes, name): idx for idx, name in enumerate(LAYER_SELECT_KEYS)}
        self.action_codes = {getattr(ecodes, name): logical for name, logical in ACTION_KEYS.items()}

        # Physical keys whose press was used to switch layers (release is swallowed)
        self.swallowed: set = set()
        # Physical key -> emitted key, so a release always matches its press
        self.active_outputs: Dict[int, int] = {}

    def _find_sayodevices(self) -> List:
        matches = []
        for path in self.evdev.list_devices():
            dev = self.evdev.InputDevice(path)
            name = dev.name.lower()
            phys = (dev.phys or "").lower()
            if self.device_query in name or "8089" in phys or "8089" in name:
                if self.ecodes.EV_KEY in dev.capabilities():
                    matches.append(dev)
                    logger.info("Matched SayoDevice endpoint: '%s' (%s)", dev.name, dev.path)
        return matches

    def _create_virtual_keyboard(self):
        keys = [getattr(self.ecodes, f"KEY_{c.upper()}") for c in "abcdefghijklmnopqrstuvwxyz"]
        keys += [
            self.ecodes.KEY_UP, self.ecodes.KEY_DOWN, self.ecodes.KEY_LEFT, self.ecodes.KEY_RIGHT,
            self.ecodes.KEY_LEFTSHIFT, self.ecodes.KEY_RIGHTSHIFT,
            self.ecodes.KEY_ENTER, self.ecodes.KEY_ESC, self.ecodes.KEY_SPACE,
            self.ecodes.KEY_BACKSPACE, self.ecodes.KEY_TAB,
        ]
        cap = {self.ecodes.EV_KEY: sorted(set(keys))}
        uinput = self.evdev.UInput(cap, name="Zynthian-LayerCake-Virtual", version=0x1)
        logger.info("Virtual keyboard created (%d keys)", len(cap[self.ecodes.EV_KEY]))
        return uinput

    def _emit(self, code: int, value: int) -> None:
        self.uinput.write(self.ecodes.EV_KEY, code, value)
        self.uinput.syn()

    def _show_current(self) -> None:
        self.overlay.notify_layer(self.current_layer, self.layers[self.current_layer])

    def _handle(self, code: int, value: int) -> None:
        # value: 1 = press, 0 = release, 2 = autorepeat

        # Shift: never forwarded; pressing it shows the current layer
        if code in self.shift_codes:
            self.shift_held = value != 0
            if value == 1:
                self._show_current()
            return

        # Release / repeat of a key that was consumed for layer selection
        if code in self.swallowed:
            if value == 0:
                self.swallowed.discard(code)
            return

        # Shift + select key -> jump directly to layer
        if self.shift_held and value == 1 and code in self.layer_select:
            self.current_layer = self.layer_select[code]
            self.swallowed.add(code)
            logger.debug("Layer -> %d", self.current_layer + 1)
            self._show_current()
            return

        # Key being released/repeated that was translated on press
        if code in self.active_outputs and value != 1:
            out = self.active_outputs[code]
            if value == 0:
                del self.active_outputs[code]
            self._emit(out, value)
            return

        # Action keys A-D: translate through the active layer
        if code in self.action_codes and value == 1:
            logical = self.action_codes[code]
            target = self.layers[self.current_layer]["keys"].get(logical, logical)
            out = getattr(self.ecodes, f"KEY_{target.upper()}", None)
            if out is None:
                logger.warning("Layer %d: invalid key '%s' for '%s'", self.current_layer + 1, target, logical)
                return
            self.active_outputs[code] = out
            logger.debug("Layer %d: %s -> %s", self.current_layer + 1, logical, target)
            self._emit(out, value)
            return

        # Everything else (arrows, etc.) passes through unchanged
        self._emit(code, value)

    def run(self) -> None:
        self.uinput = self._create_virtual_keyboard()

        while True:
            logger.info("Searching for SayoDevice matching '%s'...", self.device_query)
            devs = self._find_sayodevices()
            while not devs:
                time.sleep(2.0)
                devs = self._find_sayodevices()

            self.devices = devs
            for d in self.devices:
                try:
                    d.grab()
                except Exception as exc:
                    logger.warning("Could not grab %s: %s", d.name, exc)
            logger.info("Monitoring %d endpoint(s). Ready.", len(self.devices))

            try:
                while True:
                    ready, _, _ = select.select(self.devices, [], [])
                    for dev in ready:
                        for event in dev.read():
                            if event.type == self.ecodes.EV_KEY:
                                self._handle(event.code, event.value)
            except (OSError, self.evdev.device.DeviceError) as exc:
                logger.warning("SayoDevice error: %s. Re-detecting in 2s...", exc)
                for d in self.devices:
                    try:
                        d.ungrab()
                    except Exception:
                        pass
                self.devices = []
                self.shift_held = False
                self.swallowed.clear()
                self.active_outputs.clear()
                time.sleep(2.0)


# ==============================================================================
# Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="SayoDevice 8-layer virtual keyboard daemon for Zynthian")
    parser.add_argument("--query", "-q", default="SayoDevice", help="Device name to match (default: SayoDevice)")
    parser.add_argument("--display", "-d", default=":0", help="X11 display for the overlay (default: :0)")
    parser.add_argument("--no-gui", action="store_true", help="Disable the overlay")
    parser.add_argument("--test-layers", action="store_true", help="Print the layer table and exit")
    parser.add_argument("--list-devices", "-l", action="store_true", help="List input devices and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log every translated keystroke")
    args = parser.parse_args()

    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    if len(LAYERS) != len(LAYER_SELECT_KEYS):
        logger.error("LAYERS has %d entries but LAYER_SELECT_KEYS has %d", len(LAYERS), len(LAYER_SELECT_KEYS))
        sys.exit(1)

    if args.list_devices:
        import evdev
        from evdev import ecodes
        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            caps = dev.capabilities().get(ecodes.EV_KEY, [])
            print(f"  {dev.path}: '{dev.name}' (phys: {dev.phys}) keyboard={ecodes.KEY_A in caps}")
        sys.exit(0)

    if args.test_layers:
        for idx, layer in enumerate(LAYERS):
            k = layer["keys"]
            sel = LAYER_SELECT_KEYS[idx].replace("KEY_", "")
            print(f"Shift+{sel:<5} -> {format_layer_line(idx, layer)}   "
                  f"(emits a:{k['a']} b:{k['b']} c:{k['c']} d:{k['d']})")
        sys.exit(0)

    overlay = TitleBarOverlay("" if args.no_gui else args.display)
    manager = LayerManager(LAYERS, overlay, args.query)
    worker = threading.Thread(target=manager.run, daemon=True)
    worker.start()

    try:
        if overlay.enabled:
            overlay.run_loop()
        else:
            while worker.is_alive():
                time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Exiting.")


if __name__ == "__main__":
    main()
