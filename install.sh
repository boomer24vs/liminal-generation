#!/usr/bin/env bash
# Liminal Generator installer: Python environment, dependencies, app menu shortcut.
# Usage: ./install.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

step() { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$1"; }

step "Checking Python"
if ! command -v python3 >/dev/null; then
    echo "python3 not found: install Python 3.12 or newer with your package manager." >&2
    exit 1
fi
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || {
    echo "Python 3.12 or newer is required (found $(python3 --version))." >&2
    exit 1
}
python3 --version

step "Checking tkinter"
python3 -c 'import tkinter' 2>/dev/null || {
    echo "tkinter is missing (it cannot be installed with pip)." >&2
    echo "Fedora: sudo dnf install python3-tkinter   Debian/Ubuntu: sudo apt install python3-tk" >&2
    exit 1
}
echo "ok"

step "Creating the virtual environment (.venv) and installing dependencies"
python3 -m venv .venv || {
    echo "Could not create the venv. On Debian/Ubuntu: sudo apt install python3-venv" >&2
    exit 1
}
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

if ! command -v zenity >/dev/null; then
    warn "zenity not found: \"Save\" will use the basic Tk dialog instead of the native one (optional)."
fi

step "Adding Liminal Generator to the application menu"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$APPS"
cat > "$APPS/liminal-generator.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Liminal Generator
Comment=Generate unique liminal spaces and Backrooms photos
Exec="$DIR/.venv/bin/python" "$DIR/main.py"
Path=$DIR
Icon=$DIR/docs/media/icon.png
Terminal=false
Categories=Graphics;
DESKTOP
echo "Shortcut written to $APPS/liminal-generator.desktop"

step "Done. Launch Liminal Generator from the app menu, or run: .venv/bin/python main.py"
echo "Then click ⚙ and paste your API token (Replicate, fal.ai, OpenAI or Google)."
