#!/bin/bash
# Installs BibleChat for the current user (no password, no Python needed).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/opt/BibleChat"
mkdir -p "$HOME/.local/opt" "$HOME/.local/share/applications"
rm -rf "$DEST"
cp -r "$HERE/BibleChat" "$DEST"
cat > "$HOME/.local/share/applications/biblechat.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=BibleChat
Comment=Chat with your Bibles (opens in your browser)
Exec=$DEST/BibleChat
Terminal=false
Categories=Education;
DESK
echo "Installed. Find BibleChat in your applications menu, or run: $DEST/BibleChat"
