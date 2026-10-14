#!/bin/sh
# Foundry's defaults for everyone, set while the image is built: Breeze Dark,
# and JetBrains Mono for terminals and code.
set -eu
conf=/etc/xdg/kdeglobals
kwriteconfig6 --file "$conf" --group KDE --key LookAndFeelPackage org.kde.breezedark.desktop
kwriteconfig6 --file "$conf" --group General --key ColorScheme BreezeDark
kwriteconfig6 --file "$conf" --group General --key fixed "JetBrains Mono,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1"
echo "Foundry: Breeze Dark and JetBrains Mono are the defaults"
