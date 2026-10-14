#!/bin/sh
# Installs mdreader for the current user and makes it the default app for Markdown.
# Undo: rm ~/.local/bin/mdreader ~/.local/share/applications/mdreader.desktop
#       xdg-mime default org.kde.kate.desktop text/markdown text/x-markdown
set -e
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p ~/.local/bin ~/.local/share/applications
ln -sf "$here/mdreader.py" ~/.local/bin/mdreader
cat > ~/.local/share/applications/mdreader.desktop <<DESKTOP
[Desktop Entry]
Type=Application
Name=Markdown Reader
GenericName=Markdown Viewer
Comment=Read Markdown files, rendered
Exec=$HOME/.local/bin/mdreader %f
Icon=text-markdown
Terminal=false
Categories=Utility;Viewer;Office;
MimeType=text/markdown;text/x-markdown;
DESKTOP
update-desktop-database ~/.local/share/applications 2>/dev/null || true
xdg-mime default mdreader.desktop text/markdown text/x-markdown
echo "Installed. Default for text/markdown: $(xdg-mime query default text/markdown)"
