#!/bin/bash

# Cerebrum Banner Display for CM4
# Shows cool ASCII art when starting services
# Save as: /opt/cerebrum/scripts/banner.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Get system info
get_system_info() {
    # Memory
    TOTAL_MEM=$(free -h | awk '/^Mem:/ {print $2}')
    USED_MEM=$(free -h | awk '/^Mem:/ {print $3}')

    # CPU
    CPU_MODEL=$(cat /proc/cpuinfo | grep "Model" | head -1 | cut -d: -f2 | xargs)
    CPU_TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 || echo "N/A")

    # Disk
    DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}')
    DISK_USED=$(df -h / | awk 'NR==2 {print $3}')
    DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')

    # Network
    CM4_IP=$(ip addr show tailscale0 2>/dev/null | grep "inet " | awk '{print $2}' | 
cut -d/ -f1 || echo "N/A")
}

# Banner with animation (optional)
show_banner() {
    clear
    echo -e "${CYAN}"
    cat << 'EOF'
   ____              _
  / ___|___ _ __ ___| |__  _ __ _   _ _ __ ___
 | |   / _ \ '__/ _ \ '_ \| '__| | | | '_ ` _ \
 | |__|  __/ | |  __/ |_) | |  | |_| | | | | | |
  \____\___|_|  \___|_.__/|_|   \__,_|_| |_| |_|

EOF
    echo -e "${NC}"
    echo -e "${MAGENTA}        Hybrid AI for Raspberry Pi CM4${NC}"
    echo ""
}

# System status - simpler boxes
show_status() {
    get_system_info

    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}              ${CYAN}System Status${NC}                  ${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo -e " ${YELLOW}Platform:${NC}    $CPU_MODEL"
    echo -e " ${YELLOW}Memory:${NC}      $USED_MEM / $TOTAL_MEM"
    echo -e " ${YELLOW}Storage:${NC}     $DISK_USED / $DISK_TOTAL (${DISK_AVAIL} 
free)"
    echo -e " ${YELLOW}CPU Temp:${NC}    $CPU_TEMP"
    echo -e " ${YELLOW}Tailscale:${NC}   $CM4_IP"
    echo -e "${GREEN}================================================${NC}"
    echo ""
}

# Service status
show_services() {
    echo -e "${CYAN}Services:${NC}"

    # Check if Cerebrum is running
    if pgrep -f "uvicorn cerebrum.api.main:app" > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Cerebrum API       (Port 7000)"
    else
        echo -e "  ${RED}✗${NC} Cerebrum API       (Not running)"
    fi

    # Check VPS connection
    if timeout 2 curl -s http://100.78.22.113:9000/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} VPS Backend        (100.78.22.113:9000)"
    else
        echo -e "  ${YELLOW}⚠${NC} VPS Backend        (Unreachable)"
    fi

    # Check Tailscale
    if systemctl is-active --quiet tailscaled 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Tailscale          (Active)"
    else
        echo -e "  ${YELLOW}⚠${NC} Tailscale          (Check status)"
    fi

    echo ""
}

# Quick actions
show_actions() {
    echo -e "${CYAN}Quick Actions:${NC}"
    echo -e "  ${YELLOW}start${NC}     - Start Cerebrum"
    echo -e "  ${YELLOW}stop${NC}      - Stop Cerebrum"
    echo -e "  ${YELLOW}restart${NC}   - Restart Cerebrum"
    echo -e "  ${YELLOW}test${NC}      - Run tests"
    echo -e "  ${YELLOW}logs${NC}      - View logs"
    echo -e "  ${YELLOW}status${NC}    - Show this screen"
    echo ""
}

# Full display
show_full() {
    show_banner
    show_status
    show_services
    show_actions
}

# Compact display (for .bashrc)
show_compact() {
    echo -e 
"${CYAN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}   ____               _                        
${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  / ___|___ _ __ ___| |__  _ __ _   _ _ __ ___ 
${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} | |   / _ \\ '__/ _ \\ '_ \\| '__| | | | '_ \` _ 
\\${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} | |__|  __/ | |  __/ |_) | |  | |_| | | | | | 
|${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  \\____\\___|_|  \\___|_.__/|_|   \\__,_|_| |_| 
|_|${CYAN}║${NC}"
    echo -e 
"${CYAN}╚════════════════════════════════════════════════╝${NC}"

    # Quick status
    get_system_info
    if pgrep -f "uvicorn cerebrum.api.main:app" > /dev/null; then
        echo -e "${GREEN}● Cerebrum running${NC} | ${YELLOW}Temp: $CPU_TEMP${NC} | 
${CYAN}IP: $CM4_IP${NC}"
    else
        echo -e "${YELLOW}○ Cerebrum stopped${NC} | Type 'cerebrum start' to begin"
    fi
    echo ""
}

# Parse arguments
case "${1:-full}" in
    full)
        show_full
        ;;
    compact)
        show_compact
        ;;
    banner)
        show_banner
        ;;
    status)
        show_status
        show_services
        ;;
    *)
        show_full
        ;;
esac
