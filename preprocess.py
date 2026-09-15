import geopandas as gpd
import geemap
import click
import state

from dotenv import load_dotenv
load_dotenv()
from modules import initialize_ee, form_task, export_all_images, get_path
from config import PRE_CONFIG

ee = initialize_ee()

PROJECT_ID = get_path('PROJECT_ID')

def mask_S2(image):
    qa = image.select('QA60')
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))

    return image.updateMask(mask).divide(10000)


def mask_L8(image):
    qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
    satMask = image.select('QA_RADSAT').eq(0)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    
    return image.addBands(thermalBands, None, True).updateMask(qaMask).updateMask(satMask)


def add_S2_indices(image):
    """
    Adding 3 indices (SAVI, NDBI, MNDWI) to Sentinel-2 collection
    """
    
    savi = image.expression(
        '((L + 1) * (NIR - RED)) / (NIR + RED + L)',
        {
            'L': 0.5,
            'NIR': image.select('B8'),
            'RED': image.select('B4')
        }
    )
    ndbi = image.normalizedDifference(['B11', 'B8'])
    mndwi = image.normalizedDifference(['B3', 'B11'])

    return image.addBands([savi.rename('SAVI'), ndbi.rename('NDBI'), mndwi.rename('MNDWI')])


def get_image(districts_ee, collection_name, band_name=None, **kwargs):

    config = {**PRE_CONFIG, **kwargs}
    collection = ee.ImageCollection(collection_name) \
        .filterDate(config['s_date'], config['e_date']) \
        .filterBounds(districts_ee) \
        .filter(ee.Filter.calendarRange(config['s_month'], config['e_month'], 'month'))

    if not band_name:

        if 'S2_SR' in collection_name:
            collection = collection.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 15)).map(mask_S2).map(add_S2_indices)
            
        elif 'LC08' in collection_name:
            collection = collection.filter(ee.Filter.lt('CLOUD_COVER', 15)).map(mask_L8)

    else:
        if 'MOD11A1' in collection_name:
            collection = collection.select(band_name).map(lambda img: img.multiply(0.02))
    
    image = collection.median().clip(districts_ee)

    return image


def compute_built_up_area(s2_image):
    """
    Function returns the area in hectares of the most probable impervious surfaces.
    Threshlods were selected empirically.
    """

    savi, savi_th = s2_image.select('SAVI'), 0.2
    ndbi, ndbi_th = s2_image.select('NDBI'), -0.1
    mndwi, mndwi_th = s2_image.select('MNDWI'), 0

    built_up_mask = ndbi.gt(ndbi_th).And(mndwi.lt(mndwi_th)).And(savi.lt(savi_th))
    return built_up_mask
    

def compute_air_multiband(districts_ee):
    air_means = {}
    air_means['NO2'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_NO2').select('tropospheric_NO2_column_number_density')
    air_means['SO2'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_SO2').select('SO2_column_number_density')
    air_means['O3'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_O3').select('O3_column_number_density')
    #spring season for CO to reduce high emission from vegetation in summer
    air_means['CO'] = get_image(districts_ee, 'COPERNICUS/S5P/OFFL/L3_CO', s_month=3, e_month=5).select('CO_column_number_density')

    images = [
        air_means[name] \
        .rename(name) \
        for name in air_means.keys()
    ]
    air_multiband = ee.Image.cat(images)

    return air_multiband


def compute_lst(districts_ee):
    lst_high_res = get_image(districts_ee, 'LANDSAT/LC08/C02/T1_L2').select('ST_B10')
    lst_low_res = get_image(districts_ee, 'MODIS/061/MOD11A1', 'LST_Day_1km')
    lst_filled = lst_high_res.unmask(lst_low_res.resample('bilinear'))

    return lst_filled

@click.command()
@click.option('--region', type=str, default=None, help='The name of the region')
@click.option('--force', '-f', is_flag=True, help='Forcefully overwrite the assets')
def main(region, force):
    if region:
        state.save_state(region)
    else:
        region = state.load_region()
        click.echo(f'Running for {region}')

    try:
        districts_gdf = gpd.read_file(get_path('LOC_DISTR_GDF'))
        districts_ee = geemap.gdf_to_ee(districts_gdf)
    except:
        print('Region polygons not found in environment variables or the data folder')
        return

    s2_image = get_image(districts_ee, 'COPERNICUS/S2_SR_HARMONIZED')
    
    tasks = {
        # Green area replaced with the vagetation density
        'savi': form_task(region, districts_ee, s2_image.select('SAVI'), 'savi', 10),
        'built_up_mask': form_task(region, districts_ee, compute_built_up_area(s2_image), 'built_up_mask', 10),
        'air_multiband': form_task(region, districts_ee, compute_air_multiband(districts_ee), 'air_multiband', 1000),
        'lst_filled': form_task(region, districts_ee, compute_lst(districts_ee), 'lst_filled', 30)
    }
    
    export_all_images(tasks, region, force)


if __name__ == '__main__':
    main()