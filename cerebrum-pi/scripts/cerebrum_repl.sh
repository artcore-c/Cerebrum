#!/bin/bash

# Cerebrum Interactive REPL
# A minimal, text-first interface for AI code generation
# Save as: /opt/cerebrum-pi/scripts/cerebrum_repl.sh
# Usage: cerebrum chat  (or  ./cerebrum_repl.sh)

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
API_URL="http://localhost:7000"
HISTORY_FILE="$HOME/.cerebrum_history"

# Default parameters
MODEL="qwen_7b"
LANGUAGE="python"
MAX_TOKENS=512
TEMPERATURE=0.2

# State
MULTILINE_MODE=false
MULTILINE_BUFFER=""

# Get terminal width
TERM_WIDTH=$(tput cols)

# Center text function
center_text() {
    local text="$1"
    local text_length=${#text}
    local padding=$(( (TERM_WIDTH - text_length) / 2 ))
    printf "%${padding}s%s\n" "" "$text"
}

# Show banner
show_banner() {
    clear
    echo -e "${CYAN}"
    center_text "   ____              _                          "
    center_text "  / ___|___ _ __ ___| |__  _ __ _   _ _ __ ___TM"
    center_text " | |   / _ \ '__/ _ \ '_ \| '__| | | | '_ \` _ \."
    center_text " | |__|  __/ | |  __/ |_) | |  | |_| | | | | | |"
    center_text "  \____\___|_|  \___|_.__/|_|   \__,_|_| |_| |_|"
    echo ""
    echo -e "${MAGENTA}"
    center_text "Interactive AI Code Generation Shell"
    echo ""
    echo -e "${GRAY}"
    center_text "CerebrumTM © 2025 Robert Hall. All rights reserved"
    echo ""
}

# Show current settings
show_settings() {
    echo -e "${CYAN}Current Settings:${NC}"
    echo -e "  Model:       ${GREEN}$MODEL${NC}"
    echo -e "  Language:    ${GREEN}$LANGUAGE${NC}"
    echo -e "  Max Tokens:  ${GREEN}$MAX_TOKENS${NC}"
    echo -e "  Temperature: ${GREEN}$TEMPERATURE${NC}"
    echo ""
}

# Show prompt
show_prompt() {
    echo -e "${GRAY}Type your prompt and press Enter. Use :help for commands.${NC}"
    echo ""
}

# Show help
show_help() {
    echo -e "${CYAN}Cerebrum REPL Commands:${NC}"
    echo ""
    echo -e "  ${YELLOW}:help${NC}              Show this help"
    echo -e "  ${YELLOW}:settings${NC}          Show current settings"
    echo -e "  ${YELLOW}:model <name>${NC}      Switch model (qwen_7b, codellama_7b)"
    echo -e "  ${YELLOW}:lang <name>${NC}       Set language (python, javascript, rust, etc.)"
    echo -e "  ${YELLOW}:tokens <n>${NC}        Set max tokens (1-2048)"
    echo -e "  ${YELLOW}:temp <n>${NC}          Set temperature (0.0-2.0)"
    echo -e "  ${YELLOW}:multi${NC}             Toggle multiline mode"
    echo -e "  ${YELLOW}:clear${NC}             Clear screen"
    echo -e "  ${YELLOW}:history${NC}           Show history"
    echo -e "  ${YELLOW}:exit${NC} or ${YELLOW}:quit${NC}     Exit REPL"
    echo ""
    echo -e "${GRAY}Just type your prompt to generate code!${NC}"
    echo ""
}

# Send to API
generate() {
    local prompt="$1"

    # Show thinking indicator
    echo -e "${GRAY}Thinking...${NC}"

    # Call API
    local response=$(curl -s -X POST "$API_URL/v1/complete" \
        -H "Content-Type: application/json" \
        -d "{
            \"prompt\": $(echo "$prompt" | jq -Rs .),
            \"language\": \"$LANGUAGE\",
            \"max_tokens\": $MAX_TOKENS,
            \"temperature\": $TEMPERATURE
        }")

    # Check for errors
    if echo "$response" | jq -e '.detail' > /dev/null 2>&1; then
        local error=$(echo "$response" | jq -r '.detail.error // .detail')
        echo -e "${RED}Error: $error${NC}"
        return 1
    fi

    # Extract result
    local result=$(echo "$response" | jq -r '.result // empty')
    local tokens=$(echo "$response" | jq -r '.tokens_generated // 0')
    local time=$(echo "$response" | jq -r '.inference_time_seconds // 0')
    local source=$(echo "$response" | jq -r '.source // "unknown"')

    if [ -z "$result" ]; then
        echo -e "${RED}No response received${NC}"
        return 1
    fi

    # Display result with full-width separator
    echo ""
    printf "${GREEN}%${TERM_WIDTH}s${NC}\n" | tr ' ' '-'
    echo "$result"
    printf "${GREEN}%${TERM_WIDTH}s${NC}\n" | tr ' ' '-'
    echo -e "${GRAY}[$tokens tokens, ${time}s, $source]${NC}"
    echo ""

    # Save to history
    echo "$prompt" >> "$HISTORY_FILE"
}

# Process command
process_command() {
    local input="$1"

    case "$input" in
        :help|:h)
            show_help
            ;;
        :settings|:set)
            show_settings
            ;;
        :model\ *)
            MODEL="${input#:model }"
            echo -e "${GREEN}✓ Model set to: $MODEL${NC}"
            ;;
        :lang\ *|:language\ *)
            LANGUAGE="${input#*\ }"
            echo -e "${GREEN}✓ Language set to: $LANGUAGE${NC}"
            ;;
        :tokens\ *)
            MAX_TOKENS="${input#:tokens }"
            echo -e "${GREEN}✓ Max tokens set to: $MAX_TOKENS${NC}"
            ;;
        :temp\ *|:temperature\ *)
            TEMPERATURE="${input#*\ }"
            echo -e "${GREEN}✓ Temperature set to: $TEMPERATURE${NC}"
            ;;
        :multi|:multiline)
            MULTILINE_MODE=!$MULTILINE_MODE
            if $MULTILINE_MODE; then
                echo -e "${YELLOW}Multiline mode ON. Type :done to submit.${NC}"
            else
                echo -e "${GRAY}Multiline mode OFF${NC}"
            fi
            ;;
        :clear|:cls)
            show_banner
            show_settings
            ;;
        :history|:hist)
            if [ -f "$HISTORY_FILE" ]; then
                echo -e "${CYAN}Recent prompts:${NC}"
                tail -10 "$HISTORY_FILE" | nl
                echo ""
            else
                echo -e "${GRAY}No history yet${NC}"
            fi
            ;;
        :exit|:quit|:q)
            echo -e "${CYAN}Goodbye! ${NC}"
            exit 0
            ;;
        :*)
            echo -e "${RED}Unknown command: $input${NC}"
            echo -e "${GRAY}Type :help for available commands${NC}"
            ;;
        *)
            return 1  # Not a command, treat as prompt
            ;;
    esac

    return 0
}

# Main REPL loop
repl_loop() {
    while true; do
        # Show prompt
        if $MULTILINE_MODE; then
            echo -ne "${YELLOW}... ${NC}"
        else
            echo -ne "${BLUE}>>> ${NC}"
        fi

        # Read input
        read -r input

        # Handle empty input
        if [ -z "$input" ]; then
            continue
        fi

        # Multiline mode
        if $MULTILINE_MODE; then
            if [ "$input" = ":done" ]; then
                MULTILINE_MODE=false
                generate "$MULTILINE_BUFFER"
                MULTILINE_BUFFER=""
                continue
            elif [ "$input" = ":cancel" ]; then
                MULTILINE_MODE=false
                MULTILINE_BUFFER=""
                echo -e "${GRAY}Cancelled${NC}"
                continue
            else
                MULTILINE_BUFFER="${MULTILINE_BUFFER}${input}\n"
                continue
            fi
        fi

        # Check if it's a command
        if process_command "$input"; then
            continue
        fi

        # Generate code
        generate "$input"
    done
}

# Check if API is available
check_api() {
    if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
        echo -e "${RED}Error: Cerebrum API not available at $API_URL${NC}"
        echo ""
        echo "Start Cerebrum first:"
        echo "  cd /opt/cerebrum-pi"
        echo "  ./start.sh"
        echo ""
        exit 1
    fi
}

# Main
main() {
    # Check dependencies
    if ! command -v jq &> /dev/null; then
        echo "Installing jq..."
        sudo apt install jq -y
    fi

    # Check API
    check_api

    # Show banner
    show_banner
    show_settings

    # Start REPL
    repl_loop
}

# Run
main
