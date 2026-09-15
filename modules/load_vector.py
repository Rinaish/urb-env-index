import os
import geopandas as gpd

from config import UTM


def get_path(data_path):
    value = os.getenv(data_path)

    if value == None:
        raise ValueError(f'{data_path} not found in environment variables')
    
    return value


def _check_loc_files():
    missing = []

    loc_files = {
        key: get_path(key)
        for key in os.environ.keys() if key.startswith('LOC_')
    }

    for path in loc_files.values():
        if not os.path.isfile(path):
            missing.append(path)

    return missing


def _load_vector_layer(file_name, need_name=False):
    import geopandas as gpd

    gdf = gpd.read_file(get_path(file_name)).to_crs(UTM)
    gdf['geometry'] = gdf['geometry'].make_valid()
    gdf = gdf[~gdf.geometry.is_empty].copy()

    if need_name:
        if not 'name' in gdf.columns:
            gdf = gdf.reset_index().rename(columns={"index": "name"})
        elif gdf['name'].isna().any():
            gdf['name'] = gdf['name'].fillna(
                gdf.index.to_series().astype(str)
            )

        return gdf[['geometry', 'name']]
    else:

        return gdf[['geometry']]


def ensure_spatial_overlap(districts_gdf, ee_image):
    """
    Checks whether the district vectors belong the raster imagery from GEE assets
    """

    from shapely.geometry import box
    target_crs = 'EPSG:4326'
    
    image_coords = ee_image.geometry().bounds().coordinates().getInfo()[0]
    x = [c[0] for c in image_coords]
    y = [c[1] for c in image_coords]
    image_box = (min(x), min(y), max(x), max(y))

    distr_prev_coords = gpd.GeoSeries([box(*districts_gdf.total_bounds)], crs='EPSG:32637')
    distr_new_coords = distr_prev_coords.to_crs(target_crs)
    
    return box(*distr_new_coords.total_bounds).intersects(box(*image_box))


def load_vectors():
    missing = _check_loc_files()
    if missing:
        for path in missing:
            print(f"File {path} not found")

        return None
    else:
        return {
            'districts_gdf': _load_vector_layer('LOC_DISTR_GDF', need_name=True),
            'roads': _load_vector_layer('LOC_ROADS')
        }