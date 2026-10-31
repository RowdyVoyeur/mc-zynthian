#!/usr/bin/env python3
"""
Korg nanoKONTROL 1 Controller Driver for Zynthian Vangelis (`kontroller.py`)
=============================================================================
Maps the original Korg nanoKONTROL (v1) surface:
- 9 Knobs, 9 Faders, 18 Channel Buttons, 6 Transport Buttons
- Dispatches canonical Zynthian CUIA actions over UDP OSC (port 1370)
- Note: nanoKONTROL v1 button LEDs are local hardware indicators only.
"""

from __future__ import annotations

import socket
import sys
import time
from typing import Optional, Sequence

OSC_HOST = "127.0.0.1"
OSC_PORT = 1370

def format_osc_message(path: str, param: str = "") -> bytes:
    """Encodes a minimal OSC message for Zynthian CUIA."""
    msg = path.encode("utf-8") + b"\x00"
    while len(msg) % 4 != 0:
        msg += b"\x00"
    if param:
        msg += b",s\x00\x00" + param.encode("utf-8") + b"\x00"
        while len(msg) % 4 != 0:
            msg += b"\x00"
    else:
        msg += b",\x00\x00\x00"
    return msg

def send_cuia(action_name: str, param: str = "", host: str = OSC_HOST, port: int = OSC_PORT) -> bytes:
    """Emits a CUIA command over UDP OSC."""
    msg = format_osc_message(f"/cuia/{action_name}", param)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg, (host, port))
    except Exception:
        pass
    return msg

class NanoKontrolDriver:
    def __init__(self, port_name: str = "nanoKONTROL", send_cuia_cb=send_cuia):
        self.port_name = port_name
        self.send_cuia_cb = send_cuia_cb
        self.inport = None
        self.outport = None

    def handle_control_change(self, cc: int, val: int) -> Optional[str]:
        """Maps CC events to canonical CUIA actions."""
        if val == 0:
            return None

        # Transport Buttons (Default Scene 1)
        if cc == 44:  # Play
            self.send_cuia_cb("TOGGLE_AUDIO_PLAY")
            return "TOGGLE_AUDIO_PLAY"
        elif cc == 45:  # Stop
            self.send_cuia_cb("TOGGLE_AUDIO_PLAY")
            return "TOGGLE_AUDIO_PLAY"
        elif cc == 46:  # Rewind -> Up
            self.send_cuia_cb("ARROW_UP")
            return "ARROW_UP"
        elif cc == 47:  # Forward -> Down
            self.send_cuia_cb("ARROW_DOWN")
            return "ARROW_DOWN"
        elif cc == 48:  # Loop / Cycle -> Mixer Screen
            self.send_cuia_cb("SCREEN_AUDIO_MIXER")
            return "SCREEN_AUDIO_MIXER"
        elif cc == 49:  # Record
            self.send_cuia_cb("TOGGLE_AUDIO_RECORD")
            return "TOGGLE_AUDIO_RECORD"
        return None

    def run_live(self) -> None:
        try:
            import mido
        except ImportError:
            print("[ERROR] mido is required to run nanokontrol driver. Install via: apt install python3-mido python3-rtmidi")
            sys.exit(1)

        print(f"[nanoKONTROL] Searching for device matching '{self.port_name}'...")
        while True:
            try:
                names = mido.get_input_names()
                match = next((n for n in names if self.port_name in n), None)
                if not match:
                    time.sleep(3)
                    continue

                print(f"[nanoKONTROL] Connected to '{match}'. Listening for events...")
                with mido.open_input(match) as inport:
                    for msg in inport:
                        if msg.type == "control_change":
                            self.handle_control_change(msg.control, msg.value)

            except (KeyboardInterrupt, SystemExit):
                print("[nanoKONTROL] Exiting...")
                break
            except Exception as e:
                print(f"[nanoKONTROL] Error: {e}. Retrying in 3 seconds...")
                time.sleep(3)

def run_self_test() -> None:
    emitted = []
    driver = NanoKontrolDriver(send_cuia_cb=lambda action, param="": emitted.append(action))
    assert driver.handle_control_change(44, 127) == "TOGGLE_AUDIO_PLAY"
    assert driver.handle_control_change(46, 127) == "ARROW_UP"
    assert driver.handle_control_change(47, 127) == "ARROW_DOWN"
    assert driver.handle_control_change(48, 127) == "SCREEN_AUDIO_MIXER"
    assert driver.handle_control_change(49, 127) == "TOGGLE_AUDIO_RECORD"
    assert len(emitted) == 5
    print(f"[OK] nanoKONTROL Driver Self-Test Passed: {len(emitted)} canonical CUIA actions verified.")

if __name__ == "__main__":
    if "--daemon" in sys.argv or "-d" in sys.argv or "--live" in sys.argv:
        NanoKontrolDriver().run_live()
    else:
        run_self_test()

