import os
import click
import matplotlib.pyplot as plt
import state

from dotenv import load_dotenv
load_dotenv()
from modules import initialize_ee, load_vectors, load_rasters, ensure_spatial_overlap
from modules.criteria import *
from config import CRITERIA, CMAPS


def plot_map(gdf, col, output, region, cmap):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.axis('off')
    label = f"{col.replace('_', ' ').replace('norm', 'Normalized')}"

    gdf.plot(
        ax=ax,
        column=col,
        cmap=cmap, 
        edgecolor='black',
        linewidth=0.5,
        legend=True,
        legend_kwds={
            'label': label,
            "shrink": 0.9,
            "aspect": 25
            })

    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid.coords[0]
        ax.text(
        centroid[0],
        centroid[1],
        round(row[col], 2),
        fontsize=10,
        ha='center',
        va='center')
        
    plt.title(f'{label} in {region}')
    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches='tight')
    plt.close()


def normalize_criteria(merged_gdf):
    normalized = merged_gdf.copy()

    for crit in CRITERIA:
        col = normalized[crit]
        
        if crit in ('vegetation_density', 'air_pollution'): 
            normalized[f'norm_{crit}'] = min_max_norm(col, True)
        else:
            normalized[f'norm_{crit}'] = min_max_norm(col)
    
    return normalized


def calc_composiite_score(normalized):
    normalized['total_score'] = normalized[[f'norm_{crit}' for crit in CRITERIA]].mean(axis=1)
    normalized['norm_total_score'] = min_max_norm(normalized['total_score'], True)
        
    return normalized


def merge_res_gdf(res: dict):
    import pandas as pd
    from functools import reduce
    
    res = list(res.values())
    keep_cols = list(CRITERIA) + ['name']

    cleaned = [res[0]]
    for gdf in res[1:]:
        gdf = gdf[[col for col in keep_cols if col in gdf]]
        df = pd.DataFrame(gdf)
        cleaned.append(df)

    merged_res_gdf = reduce(lambda left, right: left.merge(right, on='name'), cleaned)
    return merged_res_gdf


def save_results(prefix, gdf, output):
    os.makedirs(f'{output}/tables', exist_ok=True)
    os.makedirs(f'{output}/geopackages', exist_ok=True)

    left_cols = ['name', 'area_ha']
    gdf.to_file(f'{output}/geopackages/total_score.gpkg', driver='GPKG')

    df = gdf.drop(columns='geometry')
    other = [c for c in df.columns if c not in left_cols]

    norm_cols = [c for c in other if     c.startswith(prefix)]
    raw_cols  = [c for c in other if not c.startswith(prefix)]

    df[left_cols + raw_cols].to_csv(f'{output}/tables/raw_values.csv',
                                     index=False, encoding='utf-8-sig')
    df[left_cols + norm_cols].to_csv(f'{output}/tables/norm_values.csv',
                                     index=False, encoding='utf-8-sig')


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