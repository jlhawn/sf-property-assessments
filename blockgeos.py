import json, os, os.path

import geopandas as gpd
import folium
from shapely.geometry import Polygon

# Ignore FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Coordinate Reference Systems.
wgs_world_mercator = 'EPSG:3395'
wgs_web_mercator_aux_shpere = 'EPSG:3857'

'''
get_block_geometries loads all of the block geometry JSON files and returns
a dictionary keyed by block number which has the points of the polygons for
each block.

The input should be a map of BlockDatum object values keyed by block_num
strings.
'''
def get_block_geometry_feature_collection(blocks):
	blocks_geometry_dir = './blocks_geometry'

	features = []

	for filepath in os.listdir(blocks_geometry_dir):
		if not filepath.endswith('.json'):
			continue

		with open(os.path.join(blocks_geometry_dir, filepath)) as geo_file:
			geo_data = json.load(geo_file)
			for geo_datum in geo_data['features']:
				block_num = geo_datum['attributes']['block_num']

				block = blocks.get(block_num)
				if block is None:
					continue

				rings = geo_datum['geometry']['rings']
				shell = rings[0]
				holes = rings[1:]

				polygon_geometry = Polygon(shell, holes)
				polygon = gpd.GeoDataFrame(index=[0], crs=wgs_world_mercator, geometry=[polygon_geometry])
				geo_json = folium.GeoJson(polygon)

				features.append({
					'type': 'Feature',
					'id': block_num,
					'properties': {
						'block': block_num,
						'land_area': block.total_land_area,
						'total_assessed_land_value': block.total_assessed_land_value,
						'avg_per_sqft_assessed_land_value': block.avg_assessed_land_value_per_area(),
						'total_extrapolated_land_value': block.total_extrapolated_land_value,
						'avg_per_sqft_extrapolated_land_value': block.avg_extrapolated_land_value_per_area(),
						'assessed_land_value_ratio': block.total_assessed_land_value / block.total_extrapolated_land_value,
					},
					'geometry': geo_json.data['features'][0]['geometry'],
				})

				if len(features) % 10 == 0:
					print(len(features))

	return {
		'type': 'FeatureCollection',
		'features': features,
	}


