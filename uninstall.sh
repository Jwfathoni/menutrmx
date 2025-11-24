#!/data/data/com.termux/files/usr/bin/bash
set -e

BASHRC="$HOME/.bashrc"
MARKER="# MENUTRMX-AUTO-MENU"

echo "Remove auto-run from .bashrc..."
if grep -q "$MARKER" "$BASHRC" 2>/dev/null; then
  sed -i "/$MARKER/,+3d" "$BASHRC"
fi

echo "Remove menu.py..."
rm -f "$HOME/menu.py"

echo "✅ Uninstall selesai. Menu tidak auto-run lagi."
