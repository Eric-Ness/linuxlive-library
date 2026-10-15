#!/bin/sh
# Once for each person, at their first login: a GIS folder in their home with
# the sample data, the sample QGIS project and the guide, bookmarked in Files.
set -eu
gis=$HOME/GIS
mkdir -p "$gis/Projects"
ln -sfn /usr/share/tiki-head/data "$gis/Sample data"
if [ ! -e "$gis/README.md" ]; then
	cp /usr/share/tiki-head/README.md "$gis/README.md"
fi
if [ -e /usr/share/tiki-head/data/world.qgz ] && [ ! -e "$gis/Projects/World.qgz" ]; then
	cp /usr/share/tiki-head/data/world.qgz "$gis/Projects/World.qgz"
fi
bookmarks=$HOME/.config/gtk-3.0/bookmarks
mkdir -p "${bookmarks%/*}"
grep -qsF "file://$gis " "$bookmarks" || printf 'file://%s GIS\n' "$gis" >>"$bookmarks"
