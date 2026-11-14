#!/usr/bin/env bash
# ==============================================================================
# mcee-audio.sh: Roland MC-101 Multi-Channel ALSA/JACK Bridge Daemon
# ==============================================================================
# Bridges the Roland MC-101 (in VENDOR USB mode: 10 capture, 4 playback at
# 44.1 kHz) into Zynthian's JACK graph using Zynthian's native 'zynain_' and
# 'zynaout_' client naming conventions and port aliases.
#
# Also disables Zynthian's built-in hotplug_audio for MC101 so Zynthian does not
# spawn an unconfigured alsa_in/alsa_out process (which lacks -r 44100 -p 64
# -n 4 -c 10, causes XRUNs/noise, and names channels "MC101 1..10").
# ==============================================================================

set -euo pipefail

ALSA_CARD="hw:MC101,DEV=0"
CAPTURE_CLIENT="zynain_mc101"
PLAYBACK_CLIENT="zynaout_mc101"
SAMPLE_RATE=44100
DEFAULT_PERIOD_SIZE=64
PERIODS=4
CUSTOM_CONFIG="/zynthian/config/zynthian_custom_config.sh"

IN_PID=""
OUT_PID=""

# Ensure Zynthian's internal hotplug_audio ignores MC101 so it doesn't fight
# with this daemon or overwrite port aliases with "MC101 1..10".
ensure_zynthian_hotplug_exclusion() {
    if [[ -d "/zynthian/config" ]]; then
        touch "$CUSTOM_CONFIG"
        chmod +x "$CUSTOM_CONFIG"
        if ! grep -q "ZYNTHIAN_HOTPLUG_AUDIO_DISABLED_IN" "$CUSTOM_CONFIG" 2>/dev/null; then
            cat << 'EOF' >> "$CUSTOM_CONFIG"

# Roland MC-101 USB Audio: managed by mcee-audio.service with -r 44100 -p 64 -n 4 -c 10/4
export ZYNTHIAN_HOTPLUG_AUDIO_DISABLED_IN="MC101"
export ZYNTHIAN_HOTPLUG_AUDIO_DISABLED_OUT="MC101"
EOF
            echo "[MC-101 Audio] Added MC101 hotplug exclusion to $CUSTOM_CONFIG"
        fi
    fi
}

stop_bridges() {
    if [[ -n "$IN_PID" ]] && kill -0 "$IN_PID" 2>/dev/null; then
        kill -9 "$IN_PID" 2>/dev/null || true
    fi
    if [[ -n "$OUT_PID" ]] && kill -0 "$OUT_PID" 2>/dev/null; then
        kill -9 "$OUT_PID" 2>/dev/null || true
    fi
    # Kill any lingering alsa_in / alsa_out targeting MC101 (including Zynthian's zynain_MC101)
    pkill -9 -f "alsa_in.*(MC101|mc101)" 2>/dev/null || true
    pkill -9 -f "alsa_out.*(MC101|mc101)" 2>/dev/null || true
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
    "zynain_mc101:capture_1":  "MC-101 Master L",
    "zynain_mc101:capture_2":  "MC-101 Master R",
    "zynain_mc101:capture_3":  "MC-101 Ch 1 L",
    "zynain_mc101:capture_4":  "MC-101 Ch 1 R",
    "zynain_mc101:capture_5":  "MC-101 Ch 2 L",
    "zynain_mc101:capture_6":  "MC-101 Ch 2 R",
    "zynain_mc101:capture_7":  "MC-101 Ch 3 L",
    "zynain_mc101:capture_8":  "MC-101 Ch 3 R",
    "zynain_mc101:capture_9":  "MC-101 Ch 4 L",
    "zynain_mc101:capture_10": "MC-101 Ch 4 R",
    "zynaout_mc101:playback_1": "MC-101 Master L",
    "zynaout_mc101:playback_2": "MC-101 Master R",
    "zynaout_mc101:playback_3": "MC-101 PC IN L",
    "zynaout_mc101:playback_4": "MC-101 PC IN R",
}

client = jack.Client("mc101_alias_helper", no_start_server=True)
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
                for old_alias in list(port.aliases):
                    try:
                        port.unset_alias(old_alias)
                    except Exception:
                        pass
                port.set_alias(label)
                applied += 1
            except Exception:
                pass
    print(f"[MC-101 Audio] Applied {applied} JACK port aliases for Zynthian UI.")
finally:
    client.close()
PY
}

ensure_zynthian_hotplug_exclusion

while true; do
    echo "[MC-101 Audio] Waiting for MC-101 USB soundcard and JACK server..."
    until grep -qi "MC101" /proc/asound/cards 2>/dev/null && jack_lsp >/dev/null 2>&1; do
        sleep 2
    done

    stop_bridges
    sleep 0.5

    # Match mc101-pisound period size (64 frames when JACK buffer <= 128; scale up if JACK buffer > 128)
    PERIOD_SIZE=$DEFAULT_PERIOD_SIZE
    if command -v jack_bufsize >/dev/null 2>&1; then
        JACK_BUF=$(jack_bufsize 2>/dev/null || echo 128)
        if [[ "$JACK_BUF" =~ ^[0-9]+$ ]] && (( JACK_BUF > 128 )); then
            PERIOD_SIZE=$(( JACK_BUF / 2 ))
        fi
    fi

    echo "[MC-101 Audio] Launching 10-channel capture bridge (${CAPTURE_CLIENT}, -r ${SAMPLE_RATE} -p ${PERIOD_SIZE} -n ${PERIODS} -c 10)..."
    alsa_in -j "$CAPTURE_CLIENT" -d "$ALSA_CARD" -r "$SAMPLE_RATE" -p "$PERIOD_SIZE" -n "$PERIODS" -c 10 >/dev/null 2>&1 &
    IN_PID=$!

    echo "[MC-101 Audio] Launching 4-channel playback bridge (${PLAYBACK_CLIENT}, -r ${SAMPLE_RATE} -p ${PERIOD_SIZE} -n ${PERIODS} -c 4)..."
    alsa_out -j "$PLAYBACK_CLIENT" -d "$ALSA_CARD" -r "$SAMPLE_RATE" -p "$PERIOD_SIZE" -n "$PERIODS" -c 4 >/dev/null 2>&1 &
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
