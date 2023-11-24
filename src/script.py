# %%
from concurrent.futures import ThreadPoolExecutor

import contextily as cx
import geopandas as gpd
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
    return width > 10 and height > 10


areas = areas[areas.geometry.apply(is_big_enough)]
largest = areas.head(3).copy()
smallest = areas.tail(3).copy()
areas = gpd.pd.concat([largest, smallest]).to_crs(epsg=4326).reset_index()

# %%
idx = 0
bbox = areas.geometry[idx].bounds

urls = find_urls(bbox)
urls

# %%
item = urls[0]
img = fetch_image(bbox, item)
img

# %%
rgbplot(img)


# # %%
# with ThreadPoolExecutor() as pool:
#     urls = list(pool.map(find_urls, areas.geometry.bounds.values.tolist()))

# areas["url"] = urls

# # %%
# areas.iloc[0, "url"] = find_urls(areas.iloc[0].geometry.bounds)

# # %%
# for i, row in areas.iterrows():
#     bbox = row.geometry.bounds
#     item = next(filter(lambda x: box(*x.bbox).contains(box(*bbox)), row["url"]))
#     areas.loc[i, "item"] = item
#     img = fetch_image(bbox, item)
#     areas.loc[i, "img"] = img

# areas
# # %%


# idx = 2

# # rgbplot(areas["img"].iloc[idx])
# ax = plt.gca()
# ax = areas.iloc[idx : idx + 1].plot(ax=ax)
# ax = GeoDataFrame(geometry=[box(*areas["item"].iloc[idx].bbox)]).plot(
#     ax=ax, color="none", edgecolor="black"
# )

# item = areas["item"].iloc[idx]

# bands = []
# for band in [4, 3, 2]:
#     with rio.open(f"{areas['img'].iloc[idx]}_B0{band}.tif") as src:
#         dat = src.read()[0]

#         dat = dat / np.quantile(dat, 0.95)
#         dat[dat >= 1] = 1
#         dat = (dat * 255).astype(np.uint16)

#         bands.append(dat)

# image = np.dstack(bands)
# plt.imshow(image)

# # %%
# areas["item"].apply(lambda x: x.bbox)
