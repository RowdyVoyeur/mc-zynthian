#!/usr/bin/env bash
# ==============================================================================
# mcee-audio.sh: Roland MC-101 Multi-Channel ALSA/JACK Bridge Daemon
# ==============================================================================
# Bridges the Roland MC-101 (in VENDOR USB mode: 10 capture, 4 playback at
# 44.1 kHz) into Zynthian's JACK graph using Zynthian's native 'zynain_' and
# 'zynaout_' client naming conventions and port aliases.
#
# This makes all MC-101 inputs and outputs appear natively inside Zynthian's
# built-in Chain Options -> Audio In and Chain Options -> Audio Out menus,
# with full Zynthian Snapshot (.zss) persistence.
# ==============================================================================

set -euo pipefail

ALSA_CARD="hw:MC101,DEV=0"
CAPTURE_CLIENT="zynain_mc101"
PLAYBACK_CLIENT="zynaout_mc101"
SAMPLE_RATE=44100
BUFFER_SIZE=64
PERIODS=4

IN_PID=""
OUT_PID=""

stop_bridges() {
    if [[ -n "$IN_PID" ]] && kill -0 "$IN_PID" 2>/dev/null; then
        kill "$IN_PID" 2>/dev/null || true
    fi
    if [[ -n "$OUT_PID" ]] && kill -0 "$OUT_PID" 2>/dev/null; then
        kill "$OUT_PID" 2>/dev/null || true
    fi
    pkill -f "alsa_in -j ${CAPTURE_CLIENT}" 2>/dev/null || true
    pkill -f "alsa_out -j ${PLAYBACK_CLIENT}" 2>/dev/null || true
    IN_PID=""
    OUT_PID=""
}

cleanup() {
    echo "[MC-101 Audio] Stopping audio bridge daemons..."
    stop_bridges
    exit 0
}

trap cleanup SIGINT SIGTERM

set_port_aliases() {
    python3 - <<'PY'
import time
import jack

aliases = {
    "zynain_mc101:capture_1": "MC-101 Master L",
    "zynain_mc101:capture_2": "MC-101 Master R",
    "zynain_mc101:capture_3": "MC-101 Track 1 L",
    "zynain_mc101:capture_4": "MC-101 Track 1 R",
    "zynain_mc101:capture_5": "MC-101 Track 2 L",
    "zynain_mc101:capture_6": "MC-101 Track 2 R",
    "zynain_mc101:capture_7": "MC-101 Track 3 L",
    "zynain_mc101:capture_8": "MC-101 Track 3 R",
    "zynain_mc101:capture_9": "MC-101 Track 4 L",
    "zynain_mc101:capture_10": "MC-101 Track 4 R",
    "zynaout_mc101:playback_1": "MC-101 Master In L",
    "zynaout_mc101:playback_2": "MC-101 Master In R",
    "zynaout_mc101:playback_3": "MC-101 PC IN L",
    "zynaout_mc101:playback_4": "MC-101 PC IN R",
}

client = jack.Client("mc101_alias_helper")
try:
    for _ in range(30):
        in_ports = client.get_ports("zynain_mc101:")
        out_ports = client.get_ports("zynaout_mc101:")
        if len(in_ports) >= 10 and len(out_ports) >= 4:
            break
        time.sleep(0.2)

    applied = 0
    for port in client.get_ports("zynain_mc101:") + client.get_ports("zynaout_mc101:"):
        label = aliases.get(port.name)
        if label:
            try:
                port.set_alias(label)
                applied += 1
            except Exception:
                pass
    print(f"[MC-101 Audio] Applied {applied} JACK port aliases for Zynthian UI.")
finally:
    client.close()
PY
}

while true; do
    echo "[MC-101 Audio] Waiting for MC-101 USB soundcard and JACK server..."
    until grep -qi "MC101" /proc/asound/cards 2>/dev/null && jack_lsp >/dev/null 2>&1; do
        sleep 2
    done

    stop_bridges

    echo "[MC-101 Audio] Launching 10-channel capture bridge (${CAPTURE_CLIENT})..."
    alsa_in -j "$CAPTURE_CLIENT" -d "$ALSA_CARD" -r "$SAMPLE_RATE" -p "$BUFFER_SIZE" -n "$PERIODS" -c 10 >/dev/null 2>&1 &
    IN_PID=$!

    echo "[MC-101 Audio] Launching 4-channel playback bridge (${PLAYBACK_CLIENT})..."
    alsa_out -j "$PLAYBACK_CLIENT" -d "$ALSA_CARD" -r "$SAMPLE_RATE" -p "$BUFFER_SIZE" -n "$PERIODS" -c 4 >/dev/null 2>&1 &
    OUT_PID=$!

    set_port_aliases || true
    echo "[MC-101 Audio] MC-101 ports registered in Zynthian Audio In / Audio Out menus."

    # Monitor bridge health and USB presence
    while grep -qi "MC101" /proc/asound/cards 2>/dev/null \
          && kill -0 "$IN_PID" 2>/dev/null \
          && kill -0 "$OUT_PID" 2>/dev/null; do
        sleep 2
    done

    echo "[MC-101 Audio] MC-101 disconnected or bridge exited. Cleaning up..."
    stop_bridges
    sleep 2
done
