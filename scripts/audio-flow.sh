#!/usr/bin/env bash
# ==============================================================================
# audio-flow.sh: Dynamic JACK Audio Routing Matrix for Zynthian & Roland MC-101
# ==============================================================================
# Based on the multi-preset architecture of mc101-pisound (RowdyVoyeur),
# adapted for Zynthian OS (Vangelis/Oram), replacing Dirtywave M8 with Zynthian.
#
# Supports:
#   - 8 dynamic routing presets (cycleable via button, macro pad, or CLI)
#   - Per-chain / per-instrument targeted routing to MC-101 USB channels
#   - Direct MC-101 stem extraction (Tracks 1-4) into Zynthian FX chains
# ==============================================================================

set -euo pipefail

PRESET_STATE_FILE="/tmp/mc101_audio_flow_preset"
TOTAL_PRESETS=8

# --- Port Definitions ---
ZYN_MASTER_L="zynmixer_bus:output_00a"
ZYN_MASTER_R="zynmixer_bus:output_00b"
ZYN_INPUT_L="zynmixer_bus:input_01a"
ZYN_INPUT_R="zynmixer_bus:input_01b"

PISOUND_IN_L="system:capture_1"
PISOUND_IN_R="system:capture_2"
PISOUND_OUT_L="system:playback_1"
PISOUND_OUT_R="system:playback_2"

# MC-101 Host Playback (from Host INTO MC-101, registered as zynaout_mc101 for Zynthian UI)
MC101_OUT_CLIENT="zynaout_mc101"
MC101_MASTER_IN_L="${MC101_OUT_CLIENT}:playback_1"   # Ch 1: Master Mix Return L
MC101_MASTER_IN_R="${MC101_OUT_CLIENT}:playback_2"   # Ch 2: Master Mix Return R
MC101_PC_IN_L="${MC101_OUT_CLIENT}:playback_3"       # Ch 3: PC IN / Track Insert L
MC101_PC_IN_R="${MC101_OUT_CLIENT}:playback_4"       # Ch 4: PC IN / Track Insert R

# MC-101 Host Capture (from MC-101 INTO Host, registered as zynain_mc101 for Zynthian UI)
MC101_IN_CLIENT="zynain_mc101"
MC101_MASTER_OUT_L="${MC101_IN_CLIENT}:capture_1"    # Ch 1: Master Mix Out L
MC101_MASTER_OUT_R="${MC101_IN_CLIENT}:capture_2"    # Ch 2: Master Mix Out R
MC101_TRK1_OUT_L="${MC101_IN_CLIENT}:capture_3"      # Ch 3: Track 1 Direct Out L
MC101_TRK1_OUT_R="${MC101_IN_CLIENT}:capture_4"      # Ch 4: Track 1 Direct Out R
MC101_TRK2_OUT_L="${MC101_IN_CLIENT}:capture_5"      # Ch 5: Track 2 Direct Out L
MC101_TRK2_OUT_R="${MC101_IN_CLIENT}:capture_6"      # Ch 6: Track 2 Direct Out R
MC101_TRK3_OUT_L="${MC101_IN_CLIENT}:capture_7"      # Ch 7: Track 3 Direct Out L
MC101_TRK3_OUT_R="${MC101_IN_CLIENT}:capture_8"      # Ch 8: Track 3 Direct Out R
MC101_TRK4_OUT_L="${MC101_IN_CLIENT}:capture_9"      # Ch 9: Track 4 Direct Out L
MC101_TRK4_OUT_R="${MC101_IN_CLIENT}:capture_10"     # Ch 10: Track 4 Direct Out R

# --- Helper Functions ---

log() {
    echo "[Audio Routing] $*"
}

connect_port() {
    local src="$1"
    local dst="$2"
    if jack_connect "$src" "$dst" 2>/dev/null; then
        echo "  + Connected: $src -> $dst"
    fi
}

disconnect_port() {
    local src="$1"
    local dst="$2"
    if jack_disconnect "$src" "$dst" 2>/dev/null; then
        echo "  - Disconnected: $src -> $dst"
    fi
}

connect_stereo() {
    connect_port "$1" "$3"
    connect_port "$2" "$4"
}

disconnect_stereo() {
    disconnect_port "$1" "$3"
    disconnect_port "$2" "$4"
}

# Disconnect all existing connections tied to MC-101 ports without breaking internal Zynthian routes
clean_mc101_connections() {
    log "Clearing existing MC-101 audio routes..."
    # Disconnect inputs to MC-101 (playback ports)
    for p in playback_1 playback_2 playback_3 playback_4; do
        if jack_lsp -c "${MC101_OUT_CLIENT}:$p" 2>/dev/null | grep -v "${MC101_OUT_CLIENT}:" >/dev/null; then
            jack_lsp -c "${MC101_OUT_CLIENT}:$p" 2>/dev/null | grep -v "${MC101_OUT_CLIENT}:" | while read -r src; do
                src=$(echo "$src" | xargs)
                [ -n "$src" ] && jack_disconnect "$src" "${MC101_OUT_CLIENT}:$p" 2>/dev/null || true
            done
        fi
    done

    # Disconnect outputs from MC-101 (capture ports)
    for i in $(seq 1 10); do
        if jack_lsp -c "${MC101_IN_CLIENT}:capture_$i" 2>/dev/null | grep -v "${MC101_IN_CLIENT}:" >/dev/null; then
            jack_lsp -c "${MC101_IN_CLIENT}:capture_$i" 2>/dev/null | grep -v "${MC101_IN_CLIENT}:" | while read -r dst; do
                dst=$(echo "$dst" | xargs)
                [ -n "$dst" ] && jack_disconnect "${MC101_IN_CLIENT}:capture_$i" "$dst" 2>/dev/null || true
            done
        fi
    done
}

# Resolve chain output ports by Chain ID (e.g., 0, 1, 2) or engine name (e.g., JC303, audioplayer)
resolve_chain_ports() {
    local query="$1"
    local left=""
    local right=""

    # 1. Check if query is numeric (Zynthian chain index 0..15)
    if [[ "$query" =~ ^[0-9]+$ ]]; then
        local pad_idx
        pad_idx=$(printf "%02d" "$query")
        # Check if mixer channel strip exists
        if jack_lsp "zynmixer_chan:output_${pad_idx}a" >/dev/null 2>&1; then
            left="zynmixer_chan:output_${pad_idx}a"
            right="zynmixer_chan:output_${pad_idx}b"
        fi
    fi

    # 2. Check engine name pattern in jack_lsp
    if [[ -z "$left" ]]; then
        local matches
        matches=$(jack_lsp 2>/dev/null | grep -i "$query" | grep -E "out|output" || true)
        left=$(echo "$matches" | head -n 1)
        right=$(echo "$matches" | sed -n '2p')
        # If engine has mono out, mirror it
        if [[ -z "$right" ]]; then
            right="$left"
        fi
    fi

    if [[ -z "$left" ]]; then
        echo "ERROR: Could not resolve ports for chain query: '$query'" >&2
        return 1
    fi

    echo "$left $right"
}

# --- 8 Routing Presets ---

apply_preset() {
    local preset="$1"
    clean_mc101_connections

    case "$preset" in
        1)
            # Preset 1: Zynthian Master -> MC-101 Master Return
            # Clean direct listening via MC-101 Master Out / Headphones
            log "Applying Preset 1: Zynthian Master -> MC-101 Master Return"
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$MC101_MASTER_IN_L" "$MC101_MASTER_IN_R"
            ;;

        2)
            # Preset 2: Zynthian Master -> MC-101 Master + Pisound Line In -> MC-101 PC IN
            # Zynthian plays to MC-101 Master Return, external gear into MC-101 Track MFX
            log "Applying Preset 2: Zynthian Master -> MC-101 Master | Pisound In -> MC-101 PC IN"
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$MC101_MASTER_IN_L" "$MC101_MASTER_IN_R"
            connect_stereo "$PISOUND_IN_L" "$PISOUND_IN_R" "$MC101_PC_IN_L" "$MC101_PC_IN_R"
            ;;

        3)
            # Preset 3: MC-101 Master + Zynthian Master -> Pisound Out
            # Parallel mix out to Pisound DAC / Main analog output
            log "Applying Preset 3: MC-101 Master + Zynthian Master -> Pisound Out (Parallel)"
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            connect_stereo "$MC101_MASTER_OUT_L" "$MC101_MASTER_OUT_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            ;;

        4)
            # Preset 4: MC-101 Master -> Zynthian Audio In / FX Chain -> Pisound Out
            # Process entire MC-101 groovebox through Zynthian LV2 / MOD-UI effects
            log "Applying Preset 4: MC-101 Master -> Zynthian FX -> Pisound Out"
            connect_stereo "$MC101_MASTER_OUT_L" "$MC101_MASTER_OUT_R" "$ZYN_INPUT_L" "$ZYN_INPUT_R"
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            ;;

        5)
            # Preset 5: Pisound In -> MC-101 PC IN -> MC-101 Master -> Zynthian FX -> Pisound Out
            # Serial mega-rig: External In -> MC-101 Track MFX -> Zynthian FX Plugins -> Pisound DAC
            log "Applying Preset 5: Pisound In -> MC-101 PC IN -> MC-101 Master -> Zynthian FX -> Pisound Out"
            connect_stereo "$PISOUND_IN_L" "$PISOUND_IN_R" "$MC101_PC_IN_L" "$MC101_PC_IN_R"
            connect_stereo "$MC101_MASTER_OUT_L" "$MC101_MASTER_OUT_R" "$ZYN_INPUT_L" "$ZYN_INPUT_R"
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            ;;

        6)
            # Preset 6: Pisound In -> MC-101 PC IN + Zynthian Master + MC-101 Master -> Pisound Out
            # External gear into MC-101 MFX; both Zynthian & MC-101 sum into Pisound Out
            log "Applying Preset 6: Pisound In -> MC-101 PC IN | MC-101 + Zynthian Master -> Pisound Out"
            connect_stereo "$PISOUND_IN_L" "$PISOUND_IN_R" "$MC101_PC_IN_L" "$MC101_PC_IN_R"
            connect_stereo "$MC101_MASTER_OUT_L" "$MC101_MASTER_OUT_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            ;;

        7)
            # Preset 7: Pisound In -> Zynthian FX -> MC-101 PC IN -> MC-101 Master -> Pisound Out
            # External gear into Zynthian FX, out into MC-101 MFX/Compressor, out to Pisound DAC
            log "Applying Preset 7: Pisound In -> Zynthian FX -> MC-101 PC IN -> MC-101 Master -> Pisound Out"
            connect_stereo "$PISOUND_IN_L" "$PISOUND_IN_R" "$ZYN_INPUT_L" "$ZYN_INPUT_R"
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$MC101_PC_IN_L" "$MC101_PC_IN_R"
            connect_stereo "$MC101_MASTER_OUT_L" "$MC101_MASTER_OUT_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            ;;

        8)
            # Preset 8: Multi-Track / Split Stem Mode
            # Chain 0 -> MC-101 PC IN (Track Insert); Master -> MC-101 Master Return; MC-101 Trk 1 -> Pisound Out
            log "Applying Preset 8: Multi-Track Split (Chain 0 -> MC-101 PC IN, Master -> MC-101 Master In)"
            if ports=$(resolve_chain_ports 0 2>/dev/null); then
                read -r c_left c_right <<< "$ports"
                connect_stereo "$c_left" "$c_right" "$MC101_PC_IN_L" "$MC101_PC_IN_R"
                log "  + Routed Chain 0 ($c_left, $c_right) -> MC-101 PC IN"
            fi
            connect_stereo "$ZYN_MASTER_L" "$ZYN_MASTER_R" "$MC101_MASTER_IN_L" "$MC101_MASTER_IN_R"
            connect_stereo "$MC101_TRK1_OUT_L" "$MC101_TRK1_OUT_R" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            ;;

        *)
            echo "Error: Invalid preset '$preset'. Valid options: 1 to $TOTAL_PRESETS" >&2
            exit 1
            ;;
    esac

    echo "$preset" > "$PRESET_STATE_FILE"
    log "Preset $preset active and saved to $PRESET_STATE_FILE"
}

# --- Targeted Routing Subcommands ---

route_chain() {
    local chain_query="$1"
    local dest="${2:-pcin}"
    local isolate="${3:-}"

    ports=$(resolve_chain_ports "$chain_query")
    read -r c_left c_right <<< "$ports"

    log "Routing Chain '$chain_query' ($c_left, $c_right) -> Destination: '$dest'..."

    # If isolation requested, disconnect from Zynthian Master Mix Bus to avoid doubling
    if [[ "$isolate" == "--isolate" || "$isolate" == "-i" ]]; then
        log "  Isolating chain: unlinking from Zynthian master bus input..."
        disconnect_stereo "$c_left" "$c_right" "zynmixer_bus:input_00a" "zynmixer_bus:input_00b"
    fi

    case "$dest" in
        pcin|insert|34)
            connect_stereo "$c_left" "$c_right" "$MC101_PC_IN_L" "$MC101_PC_IN_R"
            log "Chain '$chain_query' now streaming to MC-101 PC IN (Audio Insert for Track MFX)"
            ;;
        master|mix|12)
            connect_stereo "$c_left" "$c_right" "$MC101_MASTER_IN_L" "$MC101_MASTER_IN_R"
            log "Chain '$chain_query' now streaming to MC-101 Master Return"
            ;;
        pisound|system)
            connect_stereo "$c_left" "$c_right" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            log "Chain '$chain_query' now streaming directly to Pisound Out"
            ;;
        disconnect)
            disconnect_stereo "$c_left" "$c_right" "$MC101_PC_IN_L" "$MC101_PC_IN_R"
            disconnect_stereo "$c_left" "$c_right" "$MC101_MASTER_IN_L" "$MC101_MASTER_IN_R"
            log "Chain '$chain_query' disconnected from MC-101"
            ;;
        *)
            echo "Error: Unknown destination '$dest'. Choose from: pcin, master, pisound, disconnect" >&2
            exit 1
            ;;
    esac
}

route_track() {
    local track_num="$1"
    local dest="${2:-zynfx}"

    local trk_l=""
    local trk_r=""

    case "$track_num" in
        1) trk_l="$MC101_TRK1_OUT_L"; trk_r="$MC101_TRK1_OUT_R" ;;
        2) trk_l="$MC101_TRK2_OUT_L"; trk_r="$MC101_TRK2_OUT_R" ;;
        3) trk_l="$MC101_TRK3_OUT_L"; trk_r="$MC101_TRK3_OUT_R" ;;
        4) trk_l="$MC101_TRK4_OUT_L"; trk_r="$MC101_TRK4_OUT_R" ;;
        *)
            echo "Error: Invalid MC-101 track '$track_num'. Choose 1, 2, 3, or 4." >&2
            exit 1
            ;;
    esac

    log "Routing MC-101 Track $track_num ($trk_l, $trk_r) -> Destination: '$dest'..."

    case "$dest" in
        zynfx|zynin|main)
            connect_stereo "$trk_l" "$trk_r" "$ZYN_INPUT_L" "$ZYN_INPUT_R"
            log "MC-101 Track $track_num now streaming into Zynthian FX / Audio In"
            ;;
        pisound|system)
            connect_stereo "$trk_l" "$trk_r" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            log "MC-101 Track $track_num now streaming directly to Pisound Out"
            ;;
        disconnect)
            disconnect_stereo "$trk_l" "$trk_r" "$ZYN_INPUT_L" "$ZYN_INPUT_R"
            disconnect_stereo "$trk_l" "$trk_r" "$PISOUND_OUT_L" "$PISOUND_OUT_R"
            log "MC-101 Track $track_num disconnected"
            ;;
        *)
            # Try to resolve destination as custom chain input
            if [[ "$dest" =~ ^[0-9]+$ ]]; then
                local pad_idx
                pad_idx=$(printf "%02d" "$dest")
                connect_stereo "$trk_l" "$trk_r" "zynmixer_chan:input_${pad_idx}a" "zynmixer_chan:input_${pad_idx}b"
                log "MC-101 Track $track_num routed directly to Zynthian Chain $dest strip"
            else
                echo "Error: Unknown destination '$dest'. Choose from: zynfx, pisound, <chain_number>, disconnect" >&2
                exit 1
            fi
            ;;
    esac
}

cycle_preset() {
    local current=1
    if [[ -f "$PRESET_STATE_FILE" ]]; then
        current=$(cat "$PRESET_STATE_FILE" 2>/dev/null || echo 1)
    fi

    local next=$(( (current % TOTAL_PRESETS) + 1 ))
    log "Cycling preset: $current -> $next"
    apply_preset "$next"
}

print_status() {
    local current="1 (Default)"
    if [[ -f "$PRESET_STATE_FILE" ]]; then
        current=$(cat "$PRESET_STATE_FILE" 2>/dev/null || echo "1 (Default)")
    fi

    echo "=============================================================================="
    echo " Roland MC-101 <-> Zynthian Audio Routing Status"
    echo "=============================================================================="
    echo " Active Preset: $current of $TOTAL_PRESETS"
    echo ""
    echo " Active MC-101 Connections:"
    jack_lsp -c 2>/dev/null | grep -E -A 1 "${MC101_OUT_CLIENT}:|${MC101_IN_CLIENT}:" || echo "  (None active or JACK not running)"
    echo ""
    echo " Available Zynthian Chains:"
    jack_lsp 2>/dev/null | grep -E "zynmixer_chan:output_[0-9]{2}a" | sed 's/zynmixer_chan:output_\([0-9]*\)a/  - Chain \1/g' || echo "  (No mixer chains detected)"
    echo "=============================================================================="
}

print_help() {
    cat << EOF
Usage: $(basename "$0") <command> [arguments]

Commands:
  <1-8>                       Apply one of the 8 predefined routing presets.
  cycle                       Cycle sequentially to the next preset (1..8).
  reset                       Reset audio connections to Preset 1 (Zynthian Master -> MC-101 Master).
  status | list               Display active connections, current preset, and available chains.
  route-chain <id> <dest>     Route specific Zynthian chain (by ID or engine name) to:
                              'pcin' (Ch 3/4), 'master' (Ch 1/2), 'pisound', or 'disconnect'.
                              Add '--isolate' to remove chain from Zynthian master bus.
  route-track <1-4> <dest>    Route MC-101 direct track (1..4) to:
                              'zynfx', 'pisound', '<chain_id>', or 'disconnect'.

Presets Overview:
  1: Zynthian Master -> MC-101 Master Return (Standard monitor on MC-101)
  2: Zynthian Master -> MC-101 Master | Pisound Line In -> MC-101 PC IN (Track MFX)
  3: MC-101 Master + Zynthian Master -> Pisound Out (Parallel Mix Out)
  4: MC-101 Master -> Zynthian FX Input -> Pisound Out (Process MC-101 through Zynthian)
  5: Pisound In -> MC-101 PC IN -> MC-101 Master -> Zynthian FX -> Pisound Out (Serial Rig)
  6: Pisound In -> MC-101 PC IN | MC-101 + Zynthian Master -> Pisound Out
  7: Pisound In -> Zynthian FX -> MC-101 PC IN -> MC-101 Master -> Pisound Out
  8: Multi-Track Split (Chain 0 -> MC-101 PC IN, Master -> MC-101 Master In)
EOF
}

# --- Entry Point ---

case "${1:-}" in
    1|2|3|4|5|6|7|8)
        apply_preset "$1"
        ;;
    cycle)
        cycle_preset
        ;;
    reset)
        apply_preset 1
        ;;
    status|list)
        print_status
        ;;
    route-chain|chain)
        if [[ $# -lt 2 ]]; then
            echo "Error: 'route-chain' requires at least a chain query." >&2
            echo "Example: $(basename "$0") route-chain 0 pcin --isolate" >&2
            exit 1
        fi
        route_chain "$2" "${3:-pcin}" "${4:-}"
        ;;
    route-track|track)
        if [[ $# -lt 2 ]]; then
            echo "Error: 'route-track' requires track number (1-4)." >&2
            echo "Example: $(basename "$0") route-track 1 zynfx" >&2
            exit 1
        fi
        route_track "$2" "${3:-zynfx}"
        ;;
    help|--help|-h|"")
        print_help
        ;;
    *)
        echo "Unknown command: '$1'. Run with 'help' for available commands." >&2
        exit 1
        ;;
esac
