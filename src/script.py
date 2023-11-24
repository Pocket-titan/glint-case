# %%
import shutil
from concurrent.futures import ThreadPoolExecutor

import contextily as cx
import geopandas as gpd
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import rasterio as rio
import seaborn as sns
from folium import Figure
from geopandas import GeoDataFrame
from shapely.geometry import MultiPolygon, Point, Polygon, box
from utils import fetch_image, find_urls, rgbplot

sns.set_theme(style="ticks", palette="tab10", rc={"axes.grid": False})
pal = sns.color_palette("tab10", 10).as_hex()

dams_gdf: GeoDataFrame = gpd.read_file("../data/dams.geojson").to_crs(epsg=3857)
water_gdf: GeoDataFrame = gpd.read_file("../data/Ponds_and_Lakes.geojson").to_crs(
    epsg=3857
)
assert isinstance(dams_gdf, GeoDataFrame) and isinstance(water_gdf, GeoDataFrame)

# %%
gdf = (
    water_gdf[water_gdf["ISLAND"] == "N"]
    .drop(columns=["SHAPE_Length", "Shape_Leng", "FID", "ISLAND"])
    .rename(columns={"SHAPE_Area": "area"})
)

gdf = gpd.pd.concat(
    [
        gdf[gdf["NAME"] == " "],
        gdf[gdf["NAME"] != " "].dissolve(
            by="NAME", as_index=False, aggfunc={"area": "sum", "OBJECTID": "first"}
        ),
    ]
)

# %%
areas = gdf.sort_values(by="area", ascending=False)


def is_big_enough(x: MultiPolygon | Polygon):
    [minx, miny, maxx, maxy] = x.bounds
    [width, height] = [maxx - minx, maxy - miny]
    return width > 10 and height > 10  # resolution of bands 2, 3, 4 is 10m


areas = areas[areas.geometry.apply(is_big_enough)]
[largest, smallest] = [areas.head(3), areas.tail(3)]
areas = gpd.pd.concat([largest, smallest]).to_crs(epsg=4326).reset_index()

# %%
plt.ioff()

for i, row in areas.iterrows():
    bbox = row.geometry.bounds
    urls = find_urls(bbox)
    item = next(filter(lambda x: box(*x.bbox).contains(box(*bbox)), urls))
    image = fetch_image(bbox, item)
    rgbplot(image)
    path = f"../images/area_{i + 1}.png"
    shutil.move(f"{image}_RGB.png", path)
    areas.loc[i, "image"] = path

plt.close("all")
plt.ion()

# %%


fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(15, 10))

for i, ax in enumerate(axes.flat):
    img = mpimg.imread(areas["image"].iloc[i])
    ax.imshow(img)
    ax.axis("off")

plt.subplots_adjust(wspace=0, hspace=0)
fig.tight_layout()
