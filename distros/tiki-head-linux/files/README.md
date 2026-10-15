# Your GIS folder

Tiki Head Linux keeps your geospatial work here. `Sample data` holds Natural
Earth's world at 1:50 million (public domain) as one GeoPackage, and
`Projects/World.qgz` opens it in QGIS, styled like a chart.

## On the bench

| For | Use |
| --- | --- |
| Making maps, editing data, analysis | **QGIS** (with GRASS and SAGA in its Processing toolbox) |
| Converting and inspecting data | `ogrinfo`, `ogr2ogr`, `gdalinfo`, `gdal_translate`, `gdalwarp` |
| Coordinates and projections | `cs2cs`, `projinfo` |
| A spatial database | PostgreSQL with PostGIS: `psql` (installed systems) |
| Small spatial databases in a file | `spatialite`, SpatiaLite GUI |
| Python | `ipython3` or **Jupyter Notebook**, with GeoPandas, Rasterio, Shapely, PyProj, Fiona, xarray and Folium |
| Vector tiles for web maps | `tippecanoe` |
| OpenStreetMap | **JOSM** to edit, `osmium` to slice and convert |
| GPS tracks | `gpsbabel` |
| Climate and ocean grids | `ncdump` and `xarray` for NetCDF |

`tiki-head-gis` lists every tool and its version; `tiki-head-gis sample` opens
the sample map.

## A first five minutes

    ogrinfo -so "Sample data/natural-earth.gpkg"
    ogr2ogr -f GeoJSON countries.geojson "Sample data/natural-earth.gpkg" admin_0_countries
    tippecanoe -o countries.pmtiles -zg countries.geojson

And in Python:

    import geopandas as gpd
    world = gpd.read_file("Sample data/natural-earth.gpkg", layer="admin_0_countries")
    world.to_crs("EPSG:8857").plot(column="POP_EST")

## PostGIS

On an installed computer, your database has your user name and PostGIS in it:

    psql -c "SELECT postgis_full_version();"
    ogr2ogr -f PostgreSQL PG:dbname=$USER "Sample data/natural-earth.gpkg" admin_0_countries

In QGIS: Browser, PostgreSQL, New Connection, host `localhost`, your user name,
no password.
