# /opt/cerebrum-pi/scripts/cerebrum_repl.sh
# 
# Cerebrum Streaming REPL (Optimized) - minimal
# A minimal, text-first interface for AI code generation
# Usage: ./cerebrum_repl.sh

set -u

# ─────────────────────────────
# Colors
# ─────────────────────────────

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
RED='\033[0;31m'
NC='\033[0m'

# ─────────────────────────────
# Config
# ─────────────────────────────

API_URL="http://localhost:7000"
HISTORY_FILE="$HOME/.cerebrum_history"

MODEL="qwen_7b"
LANGUAGE="python"
MAX_TOKENS=512
TEMPERATURE=0.2

MULTILINE_MODE=false
MULTILINE_FILE=""

TERM_WIDTH=$(tput cols 2>/dev/null || echo 80)

# ─────────────────────────────
# Helpers
# ─────────────────────────────

hr() {
    printf "%${TERM_WIDTH}s\n" | tr ' ' '-'
}

center() {
    local s="$1"
    printf "%*s\n" $(( (TERM_WIDTH + ${#s}) / 2 )) "$s"
}

# ─────────────────────────────
# UI
# ─────────────────────────────

# Show banner
show_banner() {
    clear
    echo -e "${CYAN}"
    center "   ____              _                          "
    center "  / ___|___ _ __ ___| |__  _ __ _   _ _ __ ___TM"
    center " | |   / _ \ '__/ _ \ '_ \| '__| | | | '_ \` _ \ "
    center " | |__|  __/ | |  __/ |_) | |  | |_| | | | | | |"
    center "  \____\___|_|  \___|_.__/|_|   \__,_|_| |_| |_|"
    echo
    echo -e "${MAGENTA}"
    center "Distributed AI Code Assistant"
    echo
    echo -e "${GRAY}"
    center "Cerebrum™ © 2025 Robert Hall. All rights reserved"
    echo
}

show_settings() {
    echo -e "${CYAN}Settings:${NC}"
    echo "  Model:       $MODEL"
    echo "  Language:    $LANGUAGE"
    echo "  Max Tokens:  $MAX_TOKENS"
    echo "  Temperature: $TEMPERATURE"
    echo
}

show_help() {
    echo -e "${CYAN}Commands:${NC}"
    echo "  :help                Show help"
    echo "  :model <name>        Set model"
    echo "  :lang <name>         Set language"
    echo "  :tokens <n>          Set max tokens"
    echo "  :temp <n>            Set temperature"
    echo "  :multi               Toggle multiline"
    echo "  :history             Show recent prompts"
    echo "  :clear               Clear screen"
    echo "  :exit                Quit"
    echo
}

# ─────────────────────────────
# API Check
# ─────────────────────────────

check_api() {
    if ! curl -sf "$API_URL/health" >/dev/null; then
        echo -e "${RED}Cerebrum API not reachable at $API_URL${NC}"
        echo "Start it with:"
        echo "  cd /opt/cerebrum-pi && ./start.sh"
        exit 1
    fi
}

# ─────────────────────────────
# Streaming Generation (KEY FIX)
# ─────────────────────────────

generate_stream() {
    local prompt="$1"

    echo -e "${GRAY}Thinking...${NC}"

    curl -N -s "$API_URL/v1/complete/stream" \
        -H "Content-Type: application/json" \
        -d "{
            \"prompt\": $(printf '%s' "$prompt" | jq -Rs .),
            \"language\": \"$LANGUAGE\",
            \"max_tokens\": $MAX_TOKENS,
            \"temperature\": $TEMPERATURE
        }" |
    while IFS= read -r line; do
        [[ "$line" == data:* ]] || continue
        payload="${line#data: }"

        if echo "$payload" | jq -e '.token' >/dev/null 2>&1; then
            echo -n "$(echo "$payload" | jq -r '.token')"
        elif echo "$payload" | jq -e '.done' >/dev/null 2>&1; then
            echo
            break
        elif echo "$payload" | jq -e '.error' >/dev/null 2>&1; then
            echo -e "\n${RED}Error:${NC} $(echo "$payload" | jq -r '.message')"
            break
        fi
    done

    echo
    hr
    echo
}

# ─────────────────────────────
# Command Handling
# ─────────────────────────────

handle_command() {
    case "$1" in
        :help) show_help ;;
        :clear) show_banner; show_settings ;;
        :history)
            tail -10 "$HISTORY_FILE" 2>/dev/null | nl
            ;;
        :model\ *) MODEL="${1#:model }" ;;
        :lang\ *) LANGUAGE="${1#:lang }" ;;
        :tokens\ *) MAX_TOKENS="${1#:tokens }" ;;
        :temp\ *) TEMPERATURE="${1#:temp }" ;;
        :multi)
            MULTILINE_MODE=!$MULTILINE_MODE
            if $MULTILINE_MODE; then
                MULTILINE_FILE=$(mktemp)
                echo -e "${YELLOW}Multiline ON — :done to submit${NC}"
            else
                rm -f "$MULTILINE_FILE"
                echo -e "${GRAY}Multiline OFF${NC}"
            fi
            ;;
        :exit|:quit) exit 0 ;;
        :) return 1 ;;
        :*) echo -e "${RED}Unknown command${NC}" ;;
        *) return 1 ;;
    esac
    return 0
}

# ─────────────────────────────
# Main Loop
# ─────────────────────────────

repl() {
    while true; do
        if $MULTILINE_MODE; then
            echo -ne "${YELLOW}... ${NC}"
        else
            echo -ne "${BLUE}>>> ${NC}"
        fi

        read -r input || continue
        [[ -z "$input" ]] && continue

        if $MULTILINE_MODE; then
            if [[ "$input" == ":done" ]]; then
                MULTILINE_MODE=false
                prompt=$(cat "$MULTILINE_FILE")
                rm -f "$MULTILINE_FILE"
                generate_stream "$prompt"
                echo "$prompt" >> "$HISTORY_FILE"
                continue
            fi
            echo "$input" >> "$MULTILINE_FILE"
            continue
        fi

        if handle_command "$input"; then
            continue
        fi

        generate_stream "$input"
        echo "$input" >> "$HISTORY_FILE"
    done
}

# ─────────────────────────────
# Entry
# ─────────────────────────────

check_api
show_banner
show_settings
repl
