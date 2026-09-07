import os
import matplotlib.pyplot as plt

from dotenv import load_dotenv
load_dotenv()
from modules.gee_auth import ee
from modules.load_data import load_all_data
from modules.criteria import *
from config import CRITERIA, CMAPS


def plot_map(gdf, col, output, cmap):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.axis('off')

    gdf.plot(
        ax=ax,
        column=col,
        cmap=cmap, 
        edgecolor='black',
        linewidth=0.5,
        legend=True,
        legend_kwds={
            'label': f"{col.replace('_', ' ').replace('norm', 'Normalized')} index",
            "shrink": 0.9,
            "aspect": 25
            },
    )

    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid.coords[0]
        ax.text(
        centroid[0],
        centroid[1],
        round(row[col], 2),
        fontsize=10,
        ha='center',
        va='center'
    )

    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches='tight')
    plt.close()


def normalize_criteria(districts_gdf, results):
    normalized = districts_gdf.copy()

    for crit in CRITERIA:
        gdf = results[crit]
        
        if crit == 'green_area' or crit == 'air_pollution': 
            normalized[f'norm_{crit}'] = min_max_norm(gdf[crit], True)
        else:
            normalized[f'norm_{crit}'] = min_max_norm(gdf[crit])
    
    return normalized


def calc_integral_idx(normalized):
    normalized['integral'] = normalized[[f'norm_{crit}' for crit in CRITERIA]].mean(axis=1)
    normalized['norm_integral'] = min_max_norm(normalized['integral'], True)
        
    return normalized


def save_results(crit, gdf):
    os.makedirs('results/geopackages', exist_ok=True)
    os.makedirs('results/tables', exist_ok=True)

    gdf.to_file(f'results/geopackages/{crit}.gpkg')
    table = gdf.drop(columns='geometry')
    table.to_csv(f'results/tables/{crit}.csv', index=False, encoding='utf-8-sig')


def main():
    data = load_all_data(ee)

    if not data:
        print('Please obtain all of the required input data.\nRun preprocessing.py if the ee assets are absent')

        return
    else:
        green_area, air, lst, bld, roads, districts_gdf = data.values()

    districts_gdf['area_ha'] = districts_gdf.geometry.area / 10000
    districts_ee = geemap.gdf_to_ee(districts_gdf)

    print('Calculating criteria...')
    results = {
    'green_area': compute_green_area(districts_ee, districts_gdf, green_area),
    'air_pollution': compute_air(districts_ee, air),
    'lst': compute_lst(districts_ee, lst),
    'build_density': compute_build_density(districts_gdf, bld),
    'road_density': compute_roads_density(districts_gdf, roads)
}
    
    normalized_gdf = normalize_criteria(districts_gdf, results)
    results['integral'] = calc_integral_idx(normalized_gdf)

    os.makedirs('results/figures', exist_ok=True)
    for crit, gdf in results.items():
        save_results(crit, gdf)
        
        plot_map(
            normalized_gdf,
            col=f'norm_{crit}',
            output=f'results/figures/{crit}.png',
            cmap=CMAPS.get(crit)
        )
        
    print('Done! Results saved')


if __name__ == '__main__':
    main()