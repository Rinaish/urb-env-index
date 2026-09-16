import os
import matplotlib.pyplot as plt

from .criteria import min_max_norm
from config import CRITERIA


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