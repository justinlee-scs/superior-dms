#!/usr/bin/env bash
set -e

cd ~/.LINUXPRACTICE/dms

# Clear existing venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip/setuptools/wheel
pip install --upgrade pip setuptools wheel

# System dependencies
sudo apt update
sudo apt install -y \
    python3-apt \
    libdbus-1-dev libdbus-glib-1-dev \
    libcairo2-dev pkg-config \
    libgirepository1.0-dev gir1.2-gtk-3.0 \
    build-essential python3-dev \
    libffi-dev libssl-dev

# Install Python packages (remove python-apt from the list!)
pip install --upgrade -r ~/dms-packages-clean.txt --ignore-installed python-apt
