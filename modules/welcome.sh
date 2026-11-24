#!/usr/bin/env bash

clear

CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
cat << "EOF"
    __  __                 __                __   ____        __  _____ __         
   / / / /_  ______  _____/ /___ _____  ____/ /  / __ \____  / /_/ __(_) /__  _____
  / /_/ / / / / __ \/ ___/ / __ `/ __ \/ __  /  / / / / __ \/ __/ /_/ / / _ \/ ___/
 / __  / /_/ / /_/ / /  / / /_/ / / / / /_/ /  / /_/ / /_/ / /_/ __/ / /  __(__  ) 
/_/ /_/\__, / .___/_/  /_/\__,_/_/ /_/\__,_/  /_____/\____/\__/_/ /_/_/\___/____/  
      /____/_/                                                                      
EOF
echo -e "${NC}"

echo -e "${BLUE}::${NC} Hyprland dotfiles deployed successfully."
echo -e "${BLUE}::${NC} Existing configs backed up to: $BKUP_DIR"
echo -e "${BLUE}::${NC} Transitioning to Zsh..."
sleep 1.5

exec zsh
