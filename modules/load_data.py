import os
import geopandas as gpd

from config import REQUIRED_ASSETS, UTM_37N


def get_path(data_path):

    value = os.getenv(data_path)

    if value == None:
        raise ValueError(f'{data_path} not found in environment variables')
    
    return value


def get_asset(asset_name):
    proj_id = get_path('PROJECT_ID')
    asset_path = f'projects/{proj_id}/assets/images/{asset_name}'
    return asset_path


def _check_ee_assets(ee):
    missing = []

    for crit in REQUIRED_ASSETS:
        path = get_asset(crit)
        try:
            ee.data.getAsset(path)

        except Exception as e:
            print(f"EE asset {path} not found")
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
            print(f"File {path} is not found")

    return missing


def _ensure_assets_exist(ee):
    missing_ee = _check_ee_assets(ee)
    missing_loc = _check_loc_files()

    return len(missing_ee) == 0 and len(missing_loc) == 0


def load_all_data(ee):
    assets_ensured = _ensure_assets_exist(ee)

    if not assets_ensured:

        return None
    else:
        return {
                'green_area': ee.Image(get_asset('green_area')),
                'air': ee.Image(get_asset('air_multiband')),
                'lst': ee.Image(get_asset('lst_filled')),
                'bld': gpd.read_file(get_path('LOC_BLD')).to_crs(UTM_37N),
                'roads': gpd.read_file(get_path('LOC_ROADS')).to_crs(UTM_37N),
                'districts_gdf': gpd.read_file(get_path('LOC_DISTR_GDF')).to_crs(UTM_37N)
            }