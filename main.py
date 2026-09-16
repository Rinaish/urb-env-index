import os
import click
import state

from dotenv import load_dotenv
load_dotenv()
from modules import initialize_ee, load_vectors, load_rasters, ensure_spatial_overlap
from modules.criteria import *
from modules.env_pipeline import *
from config import CMAPS


@click.command()
@click.option('--region', type=str, default=None, help='The name of the region')
def main(region):
    initialize_ee()

    if region:
        state.save_state(region)
    else:
        region = state.load_region()
        click.echo(f'Running for {region}')

    vectors = load_vectors()
    rasters = load_rasters(region)
    output = f'results/{region}'

    if not vectors or not rasters:
        print('Please obtain all of the required input data. Run preprocess.py if ee assets are absent')

        return
    else:
        data = vectors | rasters
        districts_gdf, roads, veg, air, lst, bld  = data.values()

    if not ensure_spatial_overlap(districts_gdf, veg):
        print(f'Spatial mismatch: vectors do not overlap with asset for {region}')

        return
    
    districts_gdf['area_ha'] = districts_gdf.geometry.area / 10000
    districts_ee = geemap.gdf_to_ee(districts_gdf)

    print('Calculating criteria...')

    results = {
    'vegetation_density': get_vegetation_density(districts_ee, veg),
    'air_pollution': get_air_pollution(districts_ee, air),
    'lst': get_lst(districts_ee, lst),
    'built_up_area': get_built_up_area(districts_ee, districts_gdf, bld),
    'road_density': get_road_density(districts_gdf, roads)
}
    
    merged_gdf = merge_res_gdf(results)
    normalized_gdf = normalize_criteria(merged_gdf)
    normalized_gdf = calc_composiite_score(normalized_gdf)

    save_results('norm_', normalized_gdf, output)

    results['total_score'] = calc_composiite_score(normalized_gdf)

    os.makedirs(f'{output}/figures', exist_ok=True)

    for crit in CRITERIA:
        plot_map(
            normalized_gdf,
            col=f'norm_{crit}',
            output=f'{output}/figures/{crit}.png',
            region=region,
            cmap=CMAPS.get(crit)
        )
        
    print(f'Done! Results saved to {output}')


if __name__ == '__main__':
    main()