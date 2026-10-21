#!/bin/sh
# Installs BibleChat for the current user: no password, no Python, nothing else needed.
# Start it any of these ways (all do the same):
#   double-click "Install BibleChat" in this folder        (easiest)
#   in a terminal in this folder:  ./install.sh            (note the dot and slash)
#   or:                            sh install.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/opt/BibleChat"
APPS="$HOME/.local/share/applications"
WAIT=""
[ "$1" = "--from-desktop" ] && WAIT=1     # started by double-click in a terminal window: keep it open at the end

finish() {
    if [ -n "$WAIT" ]; then
        printf '\nPress Enter to close this window. '
        read -r _ || true
    fi
}

echo "Installing BibleChat..."
if [ ! -x "$HERE/BibleChat/BibleChat" ]; then
    echo "The BibleChat folder is missing next to this installer. Unpack the whole download again and retry."
    finish; exit 1
fi
# a BibleChat that is still running (often kept alive by an open browser tab) would keep showing the old
# version: stop it first, then replace the old install completely
pkill -f "/BibleChat/BibleChat" >/dev/null 2>&1 || true
sleep 1
mkdir -p "$HOME/.local/opt" "$APPS"
rm -rf "$DEST"
cp -r "$HERE/BibleChat" "$DEST"
[ -f "$HERE/biblechat.png" ] && cp "$HERE/biblechat.png" "$DEST/biblechat.png"

cat > "$APPS/biblechat.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=BibleChat
Comment=Read, search and chat with your Bibles (opens in your browser)
Exec="$DEST/BibleChat"
Icon=$DEST/biblechat.png
Terminal=false
Categories=Education;
DESK
chmod +x "$APPS/biblechat.desktop"
update-desktop-database "$APPS" >/dev/null 2>&1 || true

# an icon on the desktop too, marked as trusted so a double-click starts it straight away
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
[ -n "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    cp "$APPS/biblechat.desktop" "$DESKTOP_DIR/biblechat.desktop"
    chmod +x "$DESKTOP_DIR/biblechat.desktop"
    gio set "$DESKTOP_DIR/biblechat.desktop" metadata::trusted true >/dev/null 2>&1 || true
fi

echo ""
VER="$(cat "$HERE/VERSION" 2>/dev/null || true)"
echo "Done! BibleChat ${VER:+$VER }is installed."
echo "  - Open it from your applications menu (look for BibleChat), or from the icon on your desktop."
echo "  - Starting BibleChat now: your browser opens by itself in a few seconds."
echo "  - If an old BibleChat tab is still open in your browser, close it."
nohup "$DEST/BibleChat" >/dev/null 2>&1 &
finish
