#!/usr/bin/env bash

# Update package database and install core installer prerequisites
sudo pacman -Sy
sudo pacman -S --needed --noconfirm git base-devel gum
clear
