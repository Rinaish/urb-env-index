import os
import pandas as pd
import geopandas as gpd

from config import REGION_NAME, REQUIRED_ASSETS, UTM


def get_path(data_path):

    value = os.getenv(data_path)

    if value == None:
        raise ValueError(f'{data_path} not found in environment variables')
    
    return value


_project_id = get_path('PROJECT_ID')

def load_asset(asset_name=None):
    asset_path = f'projects/{_project_id}/assets/{REGION_NAME}_images'

    if asset_name:
        return f'{asset_path}/{asset_name}'
    else:
        return asset_path


def check_ee_assets(ee):
    missing = []

    for crit in REQUIRED_ASSETS:
        path = load_asset(crit)
        try:
            ee.data.getAsset(path)

        except ee.EEException:
            missing.append(path)

    return missing


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


def _ensure_data_exist(ee):
    missing_ee = check_ee_assets(ee)
    missing_loc = _check_loc_files()

    if missing_ee:
        for path in missing_ee:
            print(f"EE asset {path} not found")

    if missing_loc:
        for path in missing_loc:
            print(f"File {path} not found")

    return len(missing_ee) == 0 and len(missing_loc) == 0


def _load_vector_layer(file_name, need_name=False):
    gdf = gpd.read_file(get_path(file_name)).to_crs(UTM)
    gdf['geometry'] = gdf['geometry'].make_valid()
    gdf = gdf[~gdf.geometry.is_empty].copy()

    if need_name:
        if not 'name' in gdf.columns:
            gdf = gdf.reset_index().rename(columns={"index": "name"})
        elif gdf['name'].isna().any():
            gdf['name'] = gdf.apply(lambda r: str(r.name) if pd.isna(r['name']) else r['name'], axis=1)

        return gdf[['geometry', 'name']]
    else:

        return gdf[['geometry']]


def load_all_data(ee):
    data_ensured = _ensure_data_exist(ee)

    if not data_ensured:

        return None
    else:
        return {
                'green_area': ee.Image(load_asset('green_area')),
                'air': ee.Image(load_asset('air_multiband')),
                'lst': ee.Image(load_asset('lst_filled')),
                'bld': _load_vector_layer('LOC_BLD'),
                'roads': _load_vector_layer('LOC_ROADS'),
                'districts_gdf': _load_vector_layer('LOC_DISTR_GDF', need_name=True)
            }