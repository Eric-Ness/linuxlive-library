#!/bin/sh
set -eu
# linuxlive.yaml has no files: entry, so these three come from here: the
# guide, the login message and the tiki-head-gis command. Each is a copy of
# its file in files/; change both together.
mkdir -p /usr/share/tiki-head
cat >/usr/share/tiki-head/README.md <<'TIKI_EOF'
# Your GIS folder

Tiki Head Linux keeps your geospatial work here. `Sample data` holds Natural
Earth's world at 1:50 million (public domain) as one GeoPackage, and
`Projects/World.qgz` opens it in QGIS, styled like a chart.

## On the bench

| For | Use |
| --- | --- |
| Making maps, editing data, analysis | **QGIS** (with GRASS in its Processing toolbox) |
| Terrain and grid analysis | **SAGA GIS**, on its own: `saga_gui`, `saga_cmd` |
| Converting and inspecting data | `ogrinfo`, `ogr2ogr`, `gdalinfo`, `gdal_translate`, `gdalwarp` |
| Coordinates and projections | `cs2cs`, `projinfo` |
| A spatial database | PostgreSQL with PostGIS: `psql` (installed systems) |
| Small spatial databases in a file | `spatialite`, SpatiaLite GUI |
| Python | `ipython3` or **Jupyter Notebook**, with GeoPandas, Rasterio, Shapely, PyProj, Fiona, xarray and Folium |
| Vector tiles for web maps | `ogr2ogr -f PMTiles` |
| OpenStreetMap | **JOSM** to edit, `osmium` to slice and convert |
| GPS tracks | `gpsbabel` |
| Climate and ocean grids | `ncdump` and `xarray` for NetCDF |

`tiki-head-gis` lists every tool and its version; `tiki-head-gis sample` opens
the sample map.

## A first five minutes

    ogrinfo -so "Sample data/natural-earth.gpkg"
    ogr2ogr -f GeoJSON countries.geojson "Sample data/natural-earth.gpkg" admin_0_countries
    ogr2ogr -f PMTiles countries.pmtiles countries.geojson

And in Python:

    import geopandas as gpd
    world = gpd.read_file("Sample data/natural-earth.gpkg", layer="admin_0_countries")
    world.to_crs("EPSG:8857").plot(column="POP_EST")

## PostGIS

On an installed computer, your database has your user name and PostGIS in it:

    psql -c "SELECT postgis_full_version();"
    ogr2ogr -f PostgreSQL PG:dbname=$USER "Sample data/natural-earth.gpkg" admin_0_countries

In QGIS: Browser, PostgreSQL, New Connection. Leave Host empty, so QGIS
connects through the local socket as you; Database is your user name; no
password. (With Host `localhost`, PostgreSQL asks for a password, and your
database role has none.)
TIKI_EOF
cat >/etc/motd <<'TIKI_EOF'
Tiki Head Linux: a geospatial workstation.
Run tiki-head-gis to see the tools, or tiki-head-gis sample to open a world map in QGIS.
TIKI_EOF
cat >/usr/bin/tiki-head-gis <<'TIKI_EOF'
#!/bin/sh
# tiki-head-gis: what is on this Tiki Head, and a quick way to the sample map.
#
#   tiki-head-gis          the GIS tools and their versions, and PostGIS's state
#   tiki-head-gis sample   open the sample world map in QGIS
set -u

if [ "${1:-}" = sample ]; then
	project=$HOME/GIS/Projects/World.qgz
	[ -e "$project" ] || project=/usr/share/tiki-head/data/world.qgz
	exec qgis "$project"
fi

pkg() { dpkg-query -W -f='${Version}' "$1" 2>/dev/null || printf 'not installed'; }
row() { printf '  %-14s %s\n' "$1" "$2"; }

echo "Tiki Head Linux: the GIS bench"
row QGIS "$(pkg qgis)"
row GRASS "$(pkg grass)"
row SAGA "$(pkg saga)"
row GDAL "$(gdalinfo --version 2>/dev/null | cut -d, -f1 | sed 's/^GDAL //')"
row PROJ "$(pkg proj-bin)"
row PostGIS "$(pkg postgis)"
row GeoPandas "$(python3 -c 'import geopandas; print(geopandas.__version__)' 2>/dev/null || printf 'not installed')"
row JOSM "$(pkg josm)"
echo
if psql -qAtc 'SELECT postgis_lib_version()' >/dev/null 2>&1; then
	echo "  PostGIS is ready: psql opens your database '$(id -un)'."
else
	echo "  PostGIS is set up when Tiki Head is installed to a disk (not in the live session)."
fi
echo "  Sample data: /usr/share/tiki-head/data (also ~/GIS/Sample data)."
echo "  Open the sample map: tiki-head-gis sample"
TIKI_EOF
chmod 0755 /usr/bin/tiki-head-gis

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
# it cannot, the data is still there to open by hand.
QT_QPA_PLATFORM=offscreen python3 - "$gpkg" "$data/world.qgz" <<'PY' || echo "Tiki Head: no sample QGIS project (the data is still in $gpkg)"
import sys
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.PyQt.QtGui import QColor

gpkg, out = sys.argv[1], sys.argv[2]
app = QgsApplication([], False)
app.initQgis()
project = QgsProject.instance()
project.setTitle("Tiki Head: the world at 1:50 million")
project.setBackgroundColor(QColor("#cfe5ea"))
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
