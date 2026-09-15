import time
import ee

from dotenv import load_dotenv
load_dotenv()
from .load_vector import get_path
from config import WGS84, REQUIRED_ASSETS

_PROJECT_ID = get_path('PROJECT_ID')

def _load_asset(region, asset_name=None):
    asset_path = f'projects/{_PROJECT_ID}/assets/{region}_images'

    if asset_name:
        return f'{asset_path}/{asset_name}'
    else:
        return asset_path


def _ensure_catalog_exist(region):
    folder_path = _load_asset(region)

    try:
        ee.data.getAsset(folder_path)
        return True
        
    except ee.EEException as e:
        err_message = str(e).lower()

        if 'not found' in err_message or 'not exist' in err_message:
            ee.data.createAsset({'type': 'Folder'}, folder_path)
            print('Folder created.')
        else:
            print(f'Could not create a folder: {e}')
        return False


def _check_ee_assets(region):
    missing = []

    for crit in REQUIRED_ASSETS:
        path = _load_asset(region, crit)
        try:
            ee.data.getAsset(path)

        except ee.EEException:
            missing.append(path)

    return missing


def _export_tracking(tasks: list):
    timeout = 3600
    start_time = time.time()
    active = True

    print('This may take time. Wait until tasks are completed\n')
    while active:
        if time.time() - start_time > timeout:
            print('Request timed out: running tasks were canceled')
            for t in tasks:
                if t.active(): 
                    t.cancel()
                    print(f'Canceled {t.status().get("description")}')
            return

        text = []
        for t in tasks:
            status = t.status()
            t_name = status.get('description')
            t_state = status.get('state')

            if t.active():
                text.append(f'{t_name} --- {t_state}')

            elif t_state == 'COMPLETED':
                text.append(f'{t_name} export {t_state}')

            elif t_state == 'FAILED':
                err_message = status.get('error_message', 'unknown error')
                print(f'\nExport failed: {err_message}')
                return
            
            elif t_state == 'CANCEL_REQUESTED':
                print('Tasks are being cancelled')
                return

        print('\r' + ' ' * 80, end='')
        print(f'\r{', '.join(text)}', end='')
        active = any(t.active() for t in tasks)

        time.sleep(10)

    print(f"\nExport to GEE completed")


def form_task(region_name, districts_ee, image, crit, scale):
    task = ee.batch.Export.image.toAsset(
    image=image,
    description=f'{crit}',
    assetId=_load_asset(region_name, crit),
    region=districts_ee.geometry(),
    scale=scale,
    crs=WGS84,
    maxPixels=1e13
)
    return task


def load_rasters(region):
    missing = _check_ee_assets(region)
    if missing:
        for path in missing:
            print(f"EE asset {path} not found")

        return None
    else:
        return {
            'veg': ee.Image(_load_asset(region, 'savi')),
            'air': ee.Image(_load_asset(region, 'air_multiband')),
            'lst': ee.Image(_load_asset(region, 'lst_filled')),
            'bld': ee.Image(_load_asset(region, 'built_up_mask')),
        }


def export_all_images(tasks: dict, region, force=False):
    """
    Manages raster imagery export tasks regarding missing assets.
    Args:
        tasks: Defined batch tasks.
        force: Flag if GEE assets overwriting is needed.
    """

    if _ensure_catalog_exist(region):

        missing = _check_ee_assets(ee, region)
        missing_names = [path.split('/')[-1] for path in missing] if missing else []
        
        if missing and not force:
            tasks_to_start = [tasks[key] for key in missing_names if key in tasks]
            for t in tasks_to_start: t.start()

            _export_tracking(tasks_to_start)

        elif force:
            assets_to_delete = list(set(tasks.keys()).difference(set(missing_names)))

            if assets_to_delete:
                for asset in assets_to_delete:
                    try:
                        ee.data.deleteAsset(_load_asset(region, asset))
                    except ee.EEException as e:
                        print(f'Failed to delete the asset {asset}: {e}')
                        return

            tasks_to_start = list(tasks.values())
            for t in tasks_to_start: t.start()

            _export_tracking(tasks_to_start)

        else: print('You already have all of the required assets')

    else:
        print('Export failed')