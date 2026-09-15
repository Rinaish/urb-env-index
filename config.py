#ASSESSMENT PARAMETERS
CRITERIA = ['vegetation_density', 'air_pollution', 'lst', 'built_up_area', 'road_density']
AIR_COMPONENT = ['NO2', 'SO2', 'O3', 'CO']

REQUIRED_ASSETS = ['savi', 'built_up_mask', 'air_multiband', 'lst_filled']

#PROJECTION
WGS84 = 'EPSG:4326'
UTM = 'EPSG:32637'

#PREPROCESSING
PRE_CONFIG = {
    's_date': '2023-01-01',
    'e_date': '2025-12-31',
    's_month': 6,
    'e_month': 8,
}

#VISUALIZATION
CMAPS = {
    "vegetation_density": "YlGn",
    "air_pollution": "YlGn",
    "lst": "YlGn",
    "built_up_area": "YlGn",
    "road_density": "YlGn",
    "total_score": "RdYlGn"
}