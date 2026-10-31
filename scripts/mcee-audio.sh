#!/usr/bin/env bash
# ==============================================================================
# mcee-audio.sh: Roland MC-101 Multi-Channel ALSA/JACK Bridge Daemon
# ==============================================================================

set -euo pipefail

ALSA_CARD="hw:MC101,DEV=0"
SAMPLE_RATE=44100
BUFFER_SIZE=64
PERIODS=4

cleanup() {
    echo "[MC-101 Audio] Stopping audio bridge daemons..."
    killall alsa_in alsa_out zita-a2j zita-j2a 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "[MC-101 Audio] Waiting for MC-101 USB soundcard to enumerate..."
while ! grep -qi "MC101" /proc/asound/cards 2>/dev/null; do
    sleep 1
done

echo "[MC-101 Audio] Launching 10-channel capture bridge (alsa_in)..."
alsa_in -j "MC101_in" -d "$ALSA_CARD" -r "$SAMPLE_RATE" -p "$BUFFER_SIZE" -n "$PERIODS" -c 10 &

echo "[MC-101 Audio] Launching 4-channel playback bridge (alsa_out)..."
alsa_out -j "MC101_out" -d "$ALSA_CARD" -r "$SAMPLE_RATE" -p "$BUFFER_SIZE" -n "$PERIODS" -c 4 &

# Wait for JACK ports to register
sleep 2

echo "[MC-101 Audio] Patching JACK connections..."
# Route MC-101 Master Out to Pisound Main Stereo Playback
jack_connect "MC101_in:capture_1" "system:playback_1" 2>/dev/null || true
jack_connect "MC101_in:capture_2" "system:playback_2" 2>/dev/null || true

# Route Pisound Stereo Inputs into MC-101 PC Input (Channels 3 & 4)
jack_connect "system:capture_1" "MC101_out:playback_3" 2>/dev/null || true
jack_connect "system:capture_2" "MC101_out:playback_4" 2>/dev/null || true

echo "[MC-101 Audio] Audio routing active. Monitoring processes..."
wait

