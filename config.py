# ASSESSMENT PARAMETERS
CRITERIA = ['green_area', 'air_pollution', 'lst', 'build_density', 'road_density']
AIR_COMPONENT = ['NO2', 'SO2', 'O3', 'CO', 'AOD']

# PROJECTION
WGS84 = "EPSG:4326"
UTM_37N = "EPSG:32637"

# DATES
START_DATE = "2022-01-01"
END_DATE = "2025-12-31"
START_MONTH=6
END_MONTH=8

# VISUALIZATION
CMAPS = {
    "green_area": "YlGn",
    "air_pollution": "YlGn",
    "lst": "YlGn",
    "build_density": "YlGn",
    "road_density": "YlGn",
    "integral": "RdYlGn"
}

# TABLE_COLUMNS
# RENAME_MAP = {
#     'area_ha': 'Площадь_га',
#     'name': 'Район',
#     'green_area': 'Озелененность',
#     'air_pollution': 'Загрязнение_воздуха',
#     'lst': 'Температура_земной_поверхности',
#     'road_density': 'Плотность_дорожной_сети',
#     'build_density': 'Застроенность',
#     'integral_idx': 'Интегральный_индекс',
#     'norm_integral_idx': 'Норм_интегральный_индекс'
# }