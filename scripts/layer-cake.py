#!/usr/bin/env python3
# ==============================================================================
# layer-cake.py: SayoDevice 12-Key Virtual Layer Manager & OSD Daemon
# ==============================================================================
# Intercepts SayoDevice physical keystrokes, provides 6 customizable software
# layers, handles Shift+Up / Shift+Down layer cycling, and renders a native
# floating On-Screen Display (OSD) notification banner directly on Zynthian's screen.
# ==============================================================================

import argparse
import logging
import os
import queue
import sys
import threading
import time
from typing import Dict, List, Optional

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MacroPad] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MacroPad")

# ==============================================================================
# Configurable Software Layers
# ==============================================================================
# Each layer defines:
#   - 'name': Reference title displayed in the on-screen banner
#   - 'keys': Mapping from physical keys ('a', 'b', 'c', 'd') to emitted keys
#   - 'labels': Brief human-readable description of each action shown on the OSD
# ==============================================================================

LAYERS: List[Dict] = [
    {
        "name": "Layer 0: Core Navigation & Transport",
        "keys": {"a": "a", "b": "b", "c": "c", "d": "d"},
        "labels": {
            "a": "Back/Menu",
            "b": "Select",
            "c": "Chain Opt",
            "d": "Mixer View",
        },
    },
    {
        "name": "Layer 1: Context Actions & Recording",
        "keys": {"a": "e", "b": "f", "c": "g", "d": "h"},
        "labels": {
            "a": "Bold Select",
            "b": "Panic (All Off)",
            "c": "Snapshots",
            "d": "Rec Audio",
        },
    },
    {
        "name": "Layer 2: Direct Screen Jumps",
        "keys": {"a": "i", "b": "j", "c": "k", "d": "l"},
        "labels": {
            "a": "Audio Mixer",
            "b": "Pattern Edit",
            "c": "Admin/Settings",
            "d": "ALSA Levels",
        },
    },
    {
        "name": "Layer 3: Preset & Coarse Navigation",
        "keys": {"a": "m", "b": "n", "c": "o", "d": "p"},
        "labels": {
            "a": "Prev Preset",
            "b": "Next Preset",
            "c": "Page Up (+10)",
            "d": "Page Down (-10)",
        },
    },
    {
        "name": "Layer 4: Performance & System Utilities",
        "keys": {"a": "q", "b": "r", "c": "s", "d": "t"},
        "labels": {
            "a": "Tap Tempo",
            "b": "Metronome",
            "c": "Toggle Alt",
            "d": "Power Menu",
        },
    },
    {
        "name": "Layer 5: Sequencer & Transport",
        "keys": {"a": "u", "b": "v", "c": "w", "d": "x"},
        "labels": {
            "a": "Play / Stop",
            "b": "MIDI Record",
            "c": "Prev Track",
            "d": "Next Track",
        },
    },
]

# Physical hardware key identifiers
KEY_NAME_MAP = {
    "a": "KEY_A",
    "b": "KEY_B",
    "c": "KEY_C",
    "d": "KEY_D",
}

# ==============================================================================
# Native On-Screen Display (OSD) Banner using Tkinter on DISPLAY=:0
# ==============================================================================

class NativeOSDBanner:
    """Renders a sleek, non-intrusive floating OSD banner on Zynthian's LCD display."""

    def __init__(self, display_str: str = ":0") -> None:
        self.enabled = False
        self.root = None
        self.title_label = None
        self.sub_label = None
        self.hide_timer_id = None
        self.event_queue: queue.Queue = queue.Queue()

        if not display_str:
            self.enabled = False
            return

        os.environ["DISPLAY"] = display_str

        try:
            import tkinter as tk
            self.tk = tk
            self.root = tk.Tk()
            self.root.title("ZynthianMacroOSD")
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.configure(bg="#12121a")

            # Screen geometry & banner positioning
            screen_width = self.root.winfo_screenwidth()
            banner_width = min(560, screen_width - 40)
            banner_height = 68
            banner_x = (screen_width - banner_width) // 2
            banner_y = 16  # Top banner location

            self.root.geometry(f"{banner_width}x{banner_height}+{banner_x}+{banner_y}")

            # Container Frame with neon accent border
            container = tk.Frame(
                self.root,
                bg="#161622",
                highlightbackground="#00e5ff",
                highlightcolor="#00e5ff",
                highlightthickness=2,
                padx=12,
                pady=6,
            )
            container.pack(fill=tk.BOTH, expand=True)

            self.title_label = tk.Label(
                container,
                text="",
                font=("DejaVu Sans", 13, "bold"),
                fg="#00e5ff",
                bg="#161622",
                anchor="center",
            )
            self.title_label.pack(fill=tk.X, expand=True)

            self.sub_label = tk.Label(
                container,
                text="",
                font=("DejaVu Sans", 9),
                fg="#dcdcdc",
                bg="#161622",
                anchor="center",
            )
            self.sub_label.pack(fill=tk.X, expand=True)

            self.root.withdraw()  # Start hidden
            self.enabled = True
            logger.info("Native Tkinter OSD display initialized on %s (%dx%d)", display_str, banner_width, banner_height)

        except Exception as exc:
            logger.warning("GUI display not available on %s (%s). Falling back to console logging.", display_str, exc)
            self.enabled = False

    def notify_layer(self, layer_idx: int, layer_data: dict) -> None:
        """Pushes a layer change request to the GUI event queue."""
        self.event_queue.put((layer_idx, layer_data))

    def _show_banner(self, layer_idx: int, layer_data: dict) -> None:
        if not self.enabled or not self.root:
            logger.info("ACTIVE LAYER: [%d] %s", layer_idx, layer_data.get("name", ""))
            return

        name = layer_data.get("name", f"Layer {layer_idx}")
        labels = layer_data.get("labels", {})
        keys = layer_data.get("keys", {})

        # Format subtitle string showing key bindings and descriptions
        sub_items = []
        for src_key in ["a", "b", "c", "d"]:
            out_key = keys.get(src_key, src_key).upper()
            label = labels.get(src_key, "")
            if label:
                sub_items.append(f"[{out_key}] {label}")
            else:
                sub_items.append(f"[{out_key}]")
        sub_text = "   •   ".join(sub_items)

        self.title_label.config(text=f"◆ {name.upper()} ◆")
        self.sub_label.config(text=sub_text)

        # Cancel any pending hide timers and reveal window
        if self.hide_timer_id is not None:
            self.root.after_cancel(self.hide_timer_id)

        self.root.deiconify()
        self.root.lift()

        # Auto-dismiss after 1800 ms (1.8 seconds)
        self.hide_timer_id = self.root.after(1800, self._hide_banner)

    def _hide_banner(self) -> None:
        if self.enabled and self.root:
            self.root.withdraw()
            self.hide_timer_id = None

    def run_loop(self) -> None:
        """Main Tkinter event processing loop."""
        if not self.enabled or not self.root:
            return

        def process_queue():
            try:
                while True:
                    layer_idx, layer_data = self.event_queue.get_nowait()
                    self._show_banner(layer_idx, layer_data)
            except queue.Empty:
                pass
            self.root.after(40, process_queue)

        self.root.after(40, process_queue)
        self.root.mainloop()


# ==============================================================================
# Hardware Key Interceptor & Virtual Keyboard Manager
# ==============================================================================

class MacroLayerManager:
    """Grabs SayoDevice events and re-emits transformed keys via Linux uinput."""

    def __init__(self, layers: List[Dict], osd: NativeOSDBanner, device_query: str = "SayoDevice") -> None:
        self.layers = layers
        self.num_layers = len(layers)
        self.current_layer_idx = 0
        self.osd = osd
        self.device_query = device_query.lower()
        self.shift_held = False

        self.evdev = None
        self.ecodes = None
        self.device = None
        self.uinput = None

        self._load_evdev()

    def _load_evdev(self) -> None:
        try:
            import evdev
            from evdev import ecodes
            self.evdev = evdev
            self.ecodes = ecodes
        except ImportError:
            logger.error("python3-evdev is not installed! Run: apt-get install -y python3-evdev")
            sys.exit(1)

    def _find_sayodevice(self) -> Optional[object]:
        """Scans /dev/input devices specifically for the SayoDevice keyboard interface."""
        devices = [self.evdev.InputDevice(path) for path in self.evdev.list_devices()]
        candidates = []

        logger.info("Scanning %d input devices for SayoDevice keyboard...", len(devices))
        for dev in devices:
            name_lower = dev.name.lower()
            phys_lower = dev.phys.lower()
            is_match = (self.device_query in name_lower or "8089" in phys_lower or "8089" in name_lower)

            if is_match:
                caps = dev.capabilities()
                key_caps = caps.get(self.ecodes.EV_KEY, [])

                # Ignore pure mouse endpoints (SayoDevice exposes composite keyboard + mouse)
                if "mouse" in name_lower and "keyboard" not in name_lower:
                    logger.debug("Skipping mouse interface: %s (%s)", dev.name, dev.path)
                    continue

                # The keyboard interface MUST possess standard alphanumeric or arrow keys
                has_keyboard_keys = (
                    self.ecodes.KEY_A in key_caps
                    or self.ecodes.KEY_UP in key_caps
                    or self.ecodes.KEY_B in key_caps
                )

                if has_keyboard_keys:
                    logger.info("Selected keyboard device: '%s' (%s, phys: %s)", dev.name, dev.path, dev.phys)
                    return dev

                candidates.append(dev)

        if candidates:
            chosen = candidates[0]
            logger.info("Selected fallback candidate device: '%s' (%s)", chosen.name, chosen.path)
            return chosen

        return None

    def _create_virtual_keyboard(self) -> object:
        """Creates a virtual uinput keyboard capable of emitting all alphanumeric keys & arrows."""
        keys_to_support = [
            self.ecodes.KEY_UP,
            self.ecodes.KEY_DOWN,
            self.ecodes.KEY_LEFT,
            self.ecodes.KEY_RIGHT,
            self.ecodes.KEY_LEFTSHIFT,
            self.ecodes.KEY_RIGHTSHIFT,
        ]
        # Register keys A through Z
        for k in range(self.ecodes.KEY_A, self.ecodes.KEY_Z + 1):
            keys_to_support.append(k)

        cap = {
            self.ecodes.EV_KEY: keys_to_support,
        }
        uinput = self.evdev.UInput(cap, name="Zynthian-MacroPad-Virtual", version=0x1)
        logger.info("Virtual keyboard created: Zynthian-MacroPad-Virtual")
        return uinput

    def switch_layer(self, direction: int) -> None:
        """Cycles active software layer and notifies the user via on-screen OSD."""
        self.current_layer_idx = (self.current_layer_idx + direction) % self.num_layers
        layer_data = self.layers[self.current_layer_idx]
        logger.info("Layer switched -> [%d] %s", self.current_layer_idx, layer_data.get("name", ""))
        self.osd.notify_layer(self.current_layer_idx, layer_data)

    def run(self) -> None:
        """Main worker loop monitoring SayoDevice connection and event stream."""
        self.uinput = self._create_virtual_keyboard()

        # Display initial startup layer banner
        self.osd.notify_layer(self.current_layer_idx, self.layers[self.current_layer_idx])

        while True:
            # 1. Connect and grab SayoDevice
            logger.info("Searching for SayoDevice hardware matching '%s'...", self.device_query)
            dev = self._find_sayodevice()
            while dev is None:
                time.sleep(2.0)
                dev = self._find_sayodevice()

            self.device = dev
            logger.info("Found SayoDevice: '%s' (%s at %s)", dev.name, dev.path, dev.phys)

            try:
                self.device.grab()
                logger.info("SayoDevice grabbed exclusively. Ready for input.")
            except Exception as exc:
                logger.warning("Could not grab device exclusively: %s (will continue reading)", exc)

            # 2. Process keystrokes
            try:
                for event in self.device.read_loop():
                    if event.type != self.ecodes.EV_KEY:
                        continue

                    key_code = event.code
                    key_value = event.value  # 1 = Press (down), 0 = Release (up), 2 = Repeat

                    # --- Track Shift Modifier (Key 4) ---
                    if key_code in (self.ecodes.KEY_LEFTSHIFT, self.ecodes.KEY_RIGHTSHIFT):
                        self.shift_held = (key_value != 0)
                        logger.info("Key 4 (Shift) %s", "HELD [Layer Switch Armed]" if self.shift_held else "RELEASED")
                        continue

                    # --- Handle Layer Switching: Shift + Up (Next Layer) ---
                    if self.shift_held and key_code == self.ecodes.KEY_UP:
                        if key_value == 1:  # Downstroke trigger
                            logger.info("Shift + Up triggered! Switching to next layer...")
                            self.switch_layer(+1)
                        continue

                    # --- Handle Layer Switching: Shift + Down (Previous Layer) ---
                    if self.shift_held and key_code == self.ecodes.KEY_DOWN:
                        if key_value == 1:  # Downstroke trigger
                            logger.info("Shift + Down triggered! Switching to previous layer...")
                            self.switch_layer(-1)
                        continue

                    # --- Dynamic Action Cluster: Keys 5, 6, 11, 12 (a, b, c, d) ---
                    char_code = None
                    if key_code == self.ecodes.KEY_A:
                        char_code = "a"
                    elif key_code == self.ecodes.KEY_B:
                        char_code = "b"
                    elif key_code == self.ecodes.KEY_C:
                        char_code = "c"
                    elif key_code == self.ecodes.KEY_D:
                        char_code = "d"

                    if char_code is not None:
                        # Translate through active layer
                        active_layer = self.layers[self.current_layer_idx]
                        target_char = active_layer["keys"].get(char_code, char_code)
                        target_keycode_name = f"KEY_{target_char.upper()}"
                        target_keycode = getattr(self.ecodes, target_keycode_name, None)

                        if target_keycode is not None:
                            if key_value == 1:
                                logger.info("Action key '%s' -> emitted '%s' (Layer %d)", char_code, target_char, self.current_layer_idx)
                            self.uinput.write(self.ecodes.EV_KEY, target_keycode, key_value)
                            self.uinput.syn()
                        continue

                    # --- Directional Arrow Keys & Others: Pass Through Cleanly ---
                    self.uinput.write(self.ecodes.EV_KEY, key_code, key_value)
                    self.uinput.syn()

            except (OSError, self.evdev.device.DeviceError) as exc:
                logger.warning("SayoDevice disconnected or communication error: %s. Re-detecting in 2s...", exc)
                try:
                    self.device.ungrab()
                except Exception:
                    pass
                self.device = None
                time.sleep(2.0)


# ==============================================================================
# Entry Point & CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="SayoDevice 12-Key Virtual Layer Daemon with OSD for Zynthian")
    parser.add_argument("--query", "-q", default="SayoDevice", help="Device name query to match (default: 'SayoDevice')")
    parser.add_argument("--display", "-d", default=":0", help="X11 DISPLAY for OSD popup (default: ':0')")
    parser.add_argument("--no-gui", action="store_true", help="Disable graphical Tkinter OSD (console output only)")
    parser.add_argument("--test-layers", action="store_true", help="Print verified layer structure and exit")
    parser.add_argument("--list-devices", "-l", action="store_true", help="List all connected Linux input devices and exit")
    args = parser.parse_args()

    if args.list_devices:
        try:
            import evdev
            from evdev import ecodes
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            print(f"Connected Input Devices ({len(devices)} found):")
            for dev in devices:
                caps = dev.capabilities().get(ecodes.EV_KEY, [])
                has_kb = (ecodes.KEY_A in caps or ecodes.KEY_UP in caps or ecodes.KEY_B in caps)
                print(f"  {dev.path}: '{dev.name}' (phys: {dev.phys}) -> Has Keyboard Keys: {has_kb}")
        except Exception as exc:
            print(f"Error listing input devices: {exc}")
        sys.exit(0)

    if args.test_layers:
        print(f"Verified {len(LAYERS)} Configured Layers:")
        for idx, l in enumerate(LAYERS):
            k = l["keys"]
            print(f"  Layer {idx}: {l['name']} -> 5:[{k['a']}], 6:[{k['b']}], 11:[{k['c']}], 12:[{k['d']}]")
        sys.exit(0)

    # Initialize OSD Banner
    osd = NativeOSDBanner(display_str=args.display) if not args.no_gui else NativeOSDBanner(display_str="")

    # Initialize Layer Manager in a background thread
    manager = MacroLayerManager(layers=LAYERS, osd=osd, device_query=args.query)
    worker_thread = threading.Thread(target=manager.run, daemon=True)
    worker_thread.start()

    # Run Tkinter mainloop on the main thread if GUI is enabled
    if osd.enabled:
        try:
            osd.run_loop()
        except KeyboardInterrupt:
            logger.info("Exiting MacroPad daemon.")
    else:
        try:
            while worker_thread.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Exiting MacroPad daemon.")


if __name__ == "__main__":
    main()
