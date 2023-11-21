# %%
import geopandas as gpd
import numpy as np
from folium import Circle
from geopandas import GeoDataFrame
from shapely.geometry import MultiPolygon, Point

dams_gdf = gpd.read_file("../data/dams.geojson")
water_gdf = gpd.read_file("../data/Ponds_and_Lakes.geojson")
assert isinstance(dams_gdf, GeoDataFrame) and isinstance(water_gdf, GeoDataFrame)

# %%
# Task a)
water_gdf.explore("SHAPE_Area")

# %%
max_area = water_gdf["SHAPE_Area"].max()
largest_body = water_gdf[water_gdf["SHAPE_Area"] == max_area]
print(largest_body)

# %%
# Task b)
ax = water_gdf.plot("SHAPE_Area", legend=True)
ax = dams_gdf.plot(ax=ax, markersize=1)


# %%
def is_in_water(point: Point, water: GeoDataFrame) -> bool:
    return water.geometry.contains(point).any()


mask = dams_gdf["geometry"].astype(object).apply(lambda x: is_in_water(x, water_gdf))
dams_gdf["in_water"] = mask

m = water_gdf.explore(opacity=0.5)
m = dams_gdf.explore(
    "in_water",
    m=m,
    marker_kwds={"radius": 7},
    cmap=["red", "green"],
    legend=True,
)
m
# %%
old_crs = water_gdf.crs
water_buffered = water_gdf.to_crs(epsg=3857).buffer(100).to_crs(old_crs)


mask2 = (
    dams_gdf["geometry"].astype(object).apply(lambda x: is_in_water(x, water_buffered))
)
dams_gdf["in_water_buffered"] = mask2

# %%
m = water_buffered.explore(opacity=0.5)
m = dams_gdf.geometry.explore(
    (mask == False) & (mask2 == True),
    m=m,
    marker_kwds={"radius": 7},
    cmap=lambda x: "green" if x else "red",
    legend=True,
)
m

# %%
