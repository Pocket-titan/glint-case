import time
import json
import shapely
import rioxarray
import shapely.geometry
import matplotlib.pyplot as plt
import geopandas as gpd
import rasterio as rio
import numpy as np
from shapely.geometry import shape
from satsearch import Search


def find_urls(bbox, max_cloud_percentage=10):
    """
    Args:
        -bbox: tuple with bounding coordinates (minx, miny, maxx, maxy) - as returned from shapely objects .bounds method
        -max_cloud_percentage: number in intervall [0,100), maximum cloud percentage to allow

    Returns: satstac.itemcollection
    """
    search_shape = shapely.geometry.box(*bbox)
    search_geojson = json.dumps(shapely.geometry.mapping(search_shape))
    bbox_search = Search(
        bbox=bbox,
        collections=["sentinel-s2-l2a-cogs"],
        datetime="2015-01-01/2022-08-31",
        query={"eo:cloud_cover": {"lt": max_cloud_percentage}},
        url="https://earth-search.aws.element84.com/v0",
    )
    return bbox_search.items()


def fetch_image(bbox, item, bands=[4, 3, 2]):
    """
    Fetches and saves subset of sentinel-2 image that is within bounding box for each band in bands.
    Args:
        -bbox: tuple with bounding coordinates (minx, miny, maxx, maxy) - as returned from shapely objects .bounds method
        -item: satstac.item.Item
    Returns:
        image_base_name: str, base image name used with all the bands
    """
    search_shape = shapely.geometry.box(*bbox)
    search_geojson = json.dumps(shapely.geometry.mapping(search_shape))
    lon, lat = search_shape.centroid.coords[:][0]
    epsg_code = get_epsg_code(lat, lon)
    gdf = gpd.read_file(search_geojson).to_crs(epsg=epsg_code)
    print(f"Starting for {item}")
    geom = gdf.geometry
    geom_l, geom_r = (
        gdf.to_crs(epsg=epsg_code - 1).geometry,
        gdf.to_crs(epsg=epsg_code + 1).geometry,
    )

    success = True
    for b in bands:
        out_name = f"{item}_B{b:02}"
        url = item.assets[f"B{b:02}"]["href"]
        success = success & retry_fetch_write(out_name, url, geom, geom_l, geom_r)
    print(f'{"success" if success else "failure"}')
    image_base_name = str(item)
    return image_base_name


def get_epsg_code(lat, lon):
    d = 6 if lat >= 0 else 7
    return int(f"32{d}{int(((lon+180)%360)//6)+1:02d}")


def retry_fetch_write(out_name, url, geom, geom_l, geom_r):
    success = False
    retries = 0
    epsg_tries = 0
    while not success and retries <= 3:
        try:
            fetch_and_write(out_name, url, geom)
            success = True
        except ValueError as ve:

            if epsg_tries == 0:
                geom = geom_l
                epsg_tries += 1
            elif epsg_tries == 1:
                geom = geom_r
                epsg_tries += 1
            else:
                retries = 10  # Move on, somethings funky
                print(f"failed for {out_name} with error{ve}")
        except Exception as oe:
            print(oe)
            retries += 1
            time.sleep(2 ** retries)
    return success


def read_imagery(path, mask_shape, crop=True):
    data = rio.open(path)
    masked, mask_transform = rio.mask.mask(dataset=data, shapes=mask_shape, crop=crop)
    return data, masked[0, :, :], mask_transform


def fetch_and_write(out_name, url, mask_shape):
    src, mask, mask_transform = read_imagery(url, mask_shape)
    with rio.Env():
        profile = src.profile
        profile.update(
            height=mask.shape[0],
            width=mask.shape[1],
            transform=mask_transform,
        )

        with rio.open(f"{out_name}.tif", "w", **profile) as dst:
            dst.write(mask.astype(profile["dtype"]), 1)
    src.close()


def rgbplot(image_base_name, bandnums=[4, 3, 2], figsize=(18, 12)):
    """
    Creates and saves a rgb images based on the bands specified in bandnums.
    image_base_name is the base name of the tif files containg the bands.
    """
    bands = []
    for bandnum in bandnums:

        with rio.open(f"{image_base_name}_B0{bandnum}.tif") as src:
            dat = src.read()[0, :, :]

            dat = dat / np.quantile(dat, 0.95)
            dat[dat >= 1] = 1
            dat = (dat * 255).astype(np.uint16)

            bands.append(dat)
    plt.figure(figsize=figsize)
    plt.imshow(np.dstack(bands))
    plt.savefig(f"{image_base_name}_RGB.png")
