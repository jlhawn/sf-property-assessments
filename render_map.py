import json, branca

geo_data = None
with open('./blocks.geojson') as geojson_file:
    geo_data = json.load(geojson_file)
    
data = {datum['id']: datum['properties'] for datum in geo_data['features']}

low_color_scale = branca.colormap.linear.Greens_05.scale(0, 150)
low_color_scale.caption = 'Land Value Per Square Foot'
mid_color_scale = branca.colormap.linear.Blues_05.scale(150, 1000)
mid_color_scale.caption = 'Land Value Per Square Foot'
high_color_scale = branca.colormap.linear.Reds_05.scale(1000, 10000)
high_color_scale.caption = 'Land Value Per Square Foot'

def style_function(feature):
    datum = data[feature['id']]
    value = datum['avg_per_sqft_extrapolated_land_value']
    min_val, max_val = 150, 1000
    fillColor = '#black'
    if value < min_val:
        fillColor = low_color_scale(value)
    elif value > max_val:
        fillColor = high_color_scale(value)
    else:
        fillColor = mid_color_scale(value)
    return {
        'fillOpacity': 0.7,
        'weight': 2,
        'color': fillColor,
        'fillColor': fillColor,
    }

sf_coords = (37.76, -122.43)
m =  folium.Map(sf_coords, zoom_start=12, tiles='cartodbpositron')

folium.GeoJson(
    geo_data,
    style_function=style_function,
    name='Extrapolated Land Value',
).add_to(m)

folium.LayerControl().add_to(m)
m.add_child(low_color_scale)
m.add_child(mid_color_scale)
m.add_child(high_color_scale)
m.save('sf_blocks.html')
