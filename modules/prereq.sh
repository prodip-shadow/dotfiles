#!/usr/bin/env bash

# Full system sync/upgrade first to avoid partial upgrades, then install prerequisites
sudo pacman -Syu --noconfirm
sudo pacman -S --needed --noconfirm git base-devel gum
clear
