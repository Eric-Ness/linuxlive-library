#!/bin/sh
# Tiki Head's defaults, set while the image is built:
#   1. Natural Earth sample data (public domain), as one GeoPackage;
#   2. a QGIS project that opens it, styled like a chart;
#   3. GNOME with the GIS tools in the dock, in the dark style.
set -eu

# 1. Sample data: countries, places, coastline, lakes and rivers at 1:50 million.
data=/usr/share/tiki-head/data
gpkg=$data/natural-earth.gpkg
mkdir -p "$data"
work=$(mktemp -d)
for layer in cultural/ne_50m_admin_0_countries cultural/ne_50m_populated_places_simple \
	physical/ne_50m_coastline physical/ne_50m_lakes physical/ne_50m_rivers_lake_centerlines; do
	name=${layer##*/}
	curl -fsSL --retry 4 --retry-delay 5 -o "$work/$name.zip" "https://naciscdn.org/naturalearth/50m/$layer.zip"
	if [ -e "$gpkg" ]; then set -- -update; else set --; fi
	ogr2ogr "$@" -f GPKG "$gpkg" "/vsizip/$work/$name.zip/$name.shp" -nln "${name#ne_50m_}" -nlt PROMOTE_TO_MULTI
	echo "Tiki Head: sample layer ${name#ne_50m_}"
done
rm -rf "$work"
ogrinfo -so "$gpkg" | sed -n 's/^[0-9]*: /  layer: /p'

# 2. A QGIS project for the sample data. QGIS runs without a screen here; if
# it cannot, the data is still there to open by hand. The project keeps
# absolute paths: first-login.sh copies it to ~/GIS/Projects, away from the
# GeoPackage, and relative ones would point at ~/GIS/Projects/natural-earth.gpkg.
QT_QPA_PLATFORM=offscreen python3 - "$gpkg" "$data/world.qgz" <<'PY' || echo "Tiki Head: no sample QGIS project (the data is still in $gpkg)"
import sys
from qgis.core import Qgis, QgsApplication, QgsProject, QgsVectorLayer
from qgis.PyQt.QtGui import QColor

gpkg, out = sys.argv[1], sys.argv[2]
app = QgsApplication([], False)
app.initQgis()
project = QgsProject.instance()
project.setTitle("Tiki Head: the world at 1:50 million")
project.setBackgroundColor(QColor("#cfe5ea"))
project.setFilePathStorage(Qgis.FilePathType.Absolute)
# Bottom to top; each one gets a chart's colours.
for layer, title, colour in [
    ("admin_0_countries", "Countries", "#efe6cc"),
    ("lakes", "Lakes", "#9cc9d6"),
    ("rivers_lake_centerlines", "Rivers", "#5f9fb3"),
    ("coastline", "Coastline", "#3c5a62"),
    ("populated_places_simple", "Places", "#b5482a"),
]:
    lyr = QgsVectorLayer(f"{gpkg}|layername={layer}", title, "ogr")
    if not lyr.isValid():
        raise SystemExit(f"cannot open {layer}")
    lyr.renderer().symbol().setColor(QColor(colour))
    project.addMapLayer(lyr)
if not project.write(out):
    raise SystemExit("cannot write the project")
print(f"Tiki Head: sample QGIS project {out}")
app.exitQgis()
PY

# 3. GNOME: the GIS tools in the dock, and the dark style. linuxlive's own
# settings (wallpaper, accent, logo) are in zz_linuxlive, which comes later
# and keeps them.
pick() {
	for id in "$@"; do
		if [ -e "/usr/share/applications/$id" ]; then
			printf "'%s'" "$id"
			return
		fi
	done
}
dock=""
for app in "$(pick org.qgis.qgis.desktop qgis.desktop)" "'org.mozilla.firefox.desktop'" \
	"$(pick org.gnome.Nautilus.desktop)" "$(pick org.gnome.Ptyxis.desktop org.gnome.Terminal.desktop)" \
	"$(pick jupyter-notebook.desktop)" "$(pick org.openstreetmap.josm.desktop josm.desktop)" \
	"$(pick org.gnome.Maps.desktop)" "'com.visualstudio.code.desktop'"; do
	[ -n "$app" ] && dock="${dock:+$dock, }$app"
done
schemas=/usr/share/glib-2.0/schemas
{
	for scope in "" ":ubuntu"; do
		printf '[org.gnome.shell%s]\nfavorite-apps=[%s]\n\n' "$scope" "$dock"
		printf '[org.gnome.desktop.interface%s]\ncolor-scheme='"'"'prefer-dark'"'"'\n\n' "$scope"
	done
} >"$schemas/60_tiki-head.gschema.override"
echo "Tiki Head: dock [$dock], dark style"
