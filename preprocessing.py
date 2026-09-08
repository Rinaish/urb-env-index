import geopandas as gpd
import geemap

from dotenv import load_dotenv
load_dotenv()
from modules.gee_auth import ee
from modules.load_data import get_path, load_asset, check_ee_assets
from config import PRE_CONFIG, WGS84


def ensure_catalog_exist():
    folder_path = load_asset()

    try:
        ee.data.getAsset(folder_path)
        
    except ee.EEException as e:
        err_message = str(e).lower()

        if 'not found' in err_message or 'not exist' in err_message:
            ee.data.createAsset({'type': 'Folder'}, folder_path)
            print('Folder created')
        else:
            print(f'Could not create a folder: {e}')
            raise


def mask_S2(image):
    qa = image.select('QA60')
    cloudBitMask = (1 << 10) | (1 << 11)
    mask = qa.bitwiseAnd(cloudBitMask).eq(0)

    return image.updateMask(mask)


def mask_L8(image):
    qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
    satMask = image.select('QA_RADSAT').eq(0)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    
    return image.addBands(thermalBands, None, True).updateMask(qaMask).updateMask(satMask)


def add_ndvi(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    return image.addBands(ndvi)


def get_image(districts_ee, collection_name, band_name=None, **kwargs):

    config = {**PRE_CONFIG, **kwargs}
    collection = ee.ImageCollection(collection_name) \
        .filterDate(config['s_date'], config['e_date']) \
        .filterBounds(districts_ee) \
        .filter(ee.Filter.calendarRange(config['s_month'], config['e_month'], 'month'))
    
    if band_name:
        if 'S2' in collection_name:
            collection = collection.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', config['cloud_cover'])).map(mask_S2).map(add_ndvi).select(band_name)

        elif 'LC08' in collection_name:
            collection = collection.filter(ee.Filter.lt('CLOUD_COVER', config['cloud_cover'])).map(mask_L8).select(band_name)

        elif 'MOD11A1' in collection_name:
            collection = collection.select(band_name).map(lambda img: img.multiply(0.02))

        else:
            collection = collection.select(band_name)
    
    image = collection.median().clip(districts_ee)

    return image


def compute_green_area(districts_ee):
    ndvi = get_image(districts_ee, 'COPERNICUS/S2_SR_HARMONIZED', 'NDVI')
    #threshold 0.3 to consider shaded vegetation sites in urban area
    green_area = (ndvi.gt(0.3)).multiply(ee.Image.pixelArea()).divide(10000).rename('green_area_ha')

    return green_area


def compute_air_multiband(districts_ee):
    air_means = {}
    air_means['AOD'] = get_image(districts_ee, 'MODIS/061/MCD19A2_GRANULES', 'Optical_Depth_047')
    air_means['NO2'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_NO2', 'tropospheric_NO2_column_number_density')
    air_means['SO2'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_SO2', 'SO2_column_number_density')
    air_means['O3'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_O3',  'O3_column_number_density')
    #spring season for CO to reduce high emition from vegetation in summer
    air_means['CO'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_CO',  'CO_column_number_density', s_month=3, e_month=5)

    images = [
        air_means[name] \
        .rename(name) \
        for name in air_means.keys()
    ]
    air_multiband = ee.Image.cat(images)

    return air_multiband


def compute_lst(districts_ee):
    lst_high_res = get_image(districts_ee, 'LANDSAT/LC08/C02/T1_L2', 'ST_B10')
    lst_low_res = get_image(districts_ee, 'MODIS/061/MOD11A1', 'LST_Day_1km')
    lst_filled = lst_high_res.unmask(lst_low_res.resample('bilinear'))

    return lst_filled


def export_image(districts_ee, image, crit, scale):
    task = ee.batch.Export.image.toAsset(
    image=image,
    description=f'{crit}',
    assetId=load_asset(crit),
    region=districts_ee.geometry(),
    scale=scale,
    crs=WGS84,
    maxPixels=1e9
)
    task.start()

def export_all_images(districts_ee):
    if check_ee_assets(ee):
        export_image(districts_ee, compute_green_area(districts_ee), 'green_area', 10)
        export_image(districts_ee, compute_air_multiband(districts_ee), 'air_multiband', 1000)
        export_image(districts_ee, compute_lst(districts_ee), 'lst_filled', 30)

        print("All images are exported to GEE Assets")


def main():
    districts_gdf = gpd.read_file(get_path('LOC_DISTR_GDF'))
    districts_ee = geemap.gdf_to_ee(districts_gdf)

    ensure_catalog_exist()
    export_all_images(districts_ee)
        

if __name__ == '__main__':
    main()