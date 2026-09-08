import geopandas as gpd
import geemap

from modules.gee_auth import ee
from config import AIR_COMPONENT, WGS84, UTM


def min_max_norm(col, stimulating=False):
    """ 
    stimulation=True: for green area and air pollution subindexes
    stimulation=False: the lesser value - the higher index and environmental wellness

    """

    max_v = col.max()
    min_v = col.min()
    norm = ((max_v - col) / (max_v - min_v)).clip(0, 1)

    return norm if not stimulating else 1 - norm


def compute_green_area(districts_ee, districts_gdf, green_area):
    stats = green_area.reduceRegions(
        collection=districts_ee,
        reducer=ee.Reducer.sum(),
        scale=30,
        crs=UTM,
        tileScale=8
    )

    green_area_gdf = geemap.ee_to_gdf(stats)
    green_area_gdf.rename(columns={'sum': 'green_area'}, inplace=True)
    green_area_gdf['green_area'] /= districts_gdf['area_ha']

    return green_area_gdf.to_crs(WGS84)


def compute_air(districts_ee, air):
    air_stats = air.reduceRegions(
        collection=districts_ee,
        reducer=ee.Reducer.mean(),
        scale=1000,
        crs=UTM,
        tileScale=8
    )

    air_stats_gdf = geemap.ee_to_gdf(air_stats)

    for comp in AIR_COMPONENT:
        air_stats_gdf[f'norm_{comp}'] = min_max_norm(air_stats_gdf[comp])

    norm_cols = [f'norm_{comp}' for comp in AIR_COMPONENT]
    air_stats_gdf['air_pollution'] = air_stats_gdf[norm_cols].mean(axis=1)

    return air_stats_gdf.to_crs(WGS84)


def compute_lst(districts_ee, lst):
    k = 273.15

    lst_stats = lst.reduceRegions(
        collection=districts_ee,
        reducer=ee.Reducer.mean(),
        scale=30,
        crs=UTM,
        tileScale=8
    )

    lst_gdf = geemap.ee_to_gdf(lst_stats)
    lst_gdf.rename(columns={'mean': 'lst'}, inplace=True)
    lst_gdf['lst'] -= k
    
    return lst_gdf.to_crs(WGS84)

# Road network density = total length of roads (km) / district area (km^2)
def compute_roads_density(districts_gdf, roads):
    roads['length_km'] = roads.geometry.length / 1000

    roads = (
        gpd.sjoin(roads, districts_gdf, how='left', predicate='intersects')
        .groupby(by='name')['length_km'].sum()
    )

    road_density_gdf = districts_gdf.join(roads, on='name')
    road_density_gdf['road_density'] = road_density_gdf['length_km'] / (road_density_gdf.geometry.area * 1e-6)
    
    return road_density_gdf.to_crs(WGS84)

# Total area of buildings (ha) / district area (ha)
def compute_build_density(districts_gdf, bld):
    bld['bld_area_ha'] = bld.geometry.area / 10000

    bld = (
        gpd.sjoin(districts_gdf, bld, how='left', predicate='intersects')
        .groupby(by='name')['bld_area_ha'].sum()
    )
    
    build_density_gdf = districts_gdf.join(bld, on='name')
    build_density_gdf['build_density'] = build_density_gdf['bld_area_ha'] / build_density_gdf['area_ha']

    return build_density_gdf.to_crs(WGS84)