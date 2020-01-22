import csv

def weighted_percentile(data, get_weight, get, percentile):
    if percentile <= 0:
        return get(data[0])
    if percentile >= 1:
        return get(data[-1])
    
    field_sum = sum(get_weight(d) for d in data)

    running_sum = 0
    for datum in data:
        running_sum += get_weight(datum)
        if running_sum/field_sum >= percentile:
            return get(datum)

    return get(datum[-1])


def weighted_average(data, get_weight, get):
    weight_sum = sum(get_weight(d) for d in data)

    running_weighted_average = 0
    for datum in data:
        weight = get_weight(datum)/weight_sum
        running_weighted_average += weight * get(datum)

    return running_weighted_average


class ParcelDatum(object):
    def __init__(self, raw_datum):
        self.raw_datum = raw_datum

        self.property_location = raw_datum['PROPLOC']
        self.neighborhood_code = raw_datum['RP1NBRCDE']

        self.block_lot = raw_datum['RP1PRCLID']
        self.block = self.block_lot[:5].strip()
        self.lot = self.block_lot[5:]

        self.property_class_code = raw_datum['RP1CLACDE']
        self.zoning_code = raw_datum['ZONE']

        self.land_area = float(raw_datum['LAREA'])
        self.assessed_land_value = float(raw_datum['RP1LNDVAL'])

        self.current_sale_date = raw_datum['RECURRSALD']
        if len(self.current_sale_date) == 6:
            self.current_sale_year = int(self.current_sale_date[:2])
        elif len(self.current_sale_date) == 5:
            self.current_sale_year = int(self.current_sale_date[:1])
        else:
            self.current_sale_year = 0
        if 20 <= self.current_sale_year <= 99:
            self.current_sale_year += 1900
        if 1 <= self.current_sale_year < 20:
            self.current_sale_year += 2000

    def clone(self):
        return ParcelDatum(self.raw_datum)

    def assessed_land_value_per_area(self):
        return self.assessed_land_value / self.land_area if self.land_area > 0 else 0

    def __repr__(self):
        return repr(self.__dict__)

class BlockDatum(object):
    def __init__(self, block):
        self.block = block

        self.is_sampled = False
        self.sample_parcels = []
        self.total_sample_land_area = 0
        self.total_sample_assessed_land_value = 0

        self.parcels = []
        self.total_land_area = 0
        self.total_assessed_land_value = 0
        self.total_extrapolated_land_value = 0

    def sample_parcel(self, parcel):
        self.is_sampled = True
        self.sample_parcels.append(parcel)
        self.total_sample_land_area += parcel.land_area
        self.total_sample_assessed_land_value += parcel.assessed_land_value

    def add_parcel(self, parcel):
        self.parcels.append(parcel)
        self.total_land_area += parcel.land_area
        self.total_assessed_land_value += parcel.assessed_land_value
        self.total_extrapolated_land_value += (parcel.land_area * self.avg_sample_assessed_land_value_per_area()) if self.is_sampled else parcel.assessed_land_value
        

    def avg_sample_assessed_land_value_per_area(self):
        return (self.total_sample_assessed_land_value / self.total_sample_land_area) if self.total_sample_land_area > 0 else 0

    def avg_assessed_land_value_per_area(self):
        return (self.total_assessed_land_value / self.total_land_area) if self.total_land_area > 0 else 0

    def avg_extrapolated_land_value_per_area(self):
        return (self.total_extrapolated_land_value / self.total_land_area) if self.total_land_area > 0 else 0


CSV_FILENAME = './2019.8.12__SF_ASR_Secured_Roll_Data_2017-2018_0.csv'

# Open the property data file and load each row as a ParcelDatum
all_parcels = []
with open(CSV_FILENAME) as csv_file:
    csv_header = None
    for csv_row in csv.reader(csv_file):
        if csv_header is None:
            csv_header = csv_row
            continue

        row = {}
        for i, field in enumerate(csv_row):
            field_name = csv_header[i]
            row[field_name] = field

        all_parcels.append(ParcelDatum(row))

print('Num Parcels: ', len(all_parcels))

sample_parcels = list(all_parcels)
# Filter this data to only the properties with relatively recent sale dates,
# where the assessed value is still relatively close to the market value.
sample_parcels = [p for p in sample_parcels if 2008 <= p.current_sale_year <= 2020]
# Some of these data entries have land parcels which are too small or too
# large to be meaningful or have land values which are too low to be
# meaningful. These are probably errors?
sample_parcels = [p for p in sample_parcels if 1000 <= p.land_area <= 400000 and p.assessed_land_value > 10000]
# Class codes Z and CZ are for condos and the parcels for these property types
# do not seem to have accurate land area or value calculations and are not
# meaningful.
sample_parcels = [p for p in sample_parcels if p.property_class_code not in {'Z', 'CZ'}]
# After sorting, I have found several properties with very low assessed land
# values which do not seem accurate. These may be from a transferred property
# tax base?
sample_parcels = [p for p in sample_parcels if p.assessed_land_value_per_area() >= 50]


def appreciate(value, rate, years):
    return value * (1+rate)**years

# This loop attempts to increase the land values of parcels by an additional
# 4 percent per year in an attempt to better match current market values.
sample_parcels = [p.clone() for p in sample_parcels]
current_year = 2019
for parcel in sample_parcels:
    if parcel.current_sale_year < current_year:
        parcel.assessed_land_value = appreciate(parcel.assessed_land_value, 0.03, current_year - parcel.current_sale_year)

print('Num Sample Parcels: ', len(sample_parcels))

# Next, group all of the sample data by block.
all_blocks = {}
for parcel in sample_parcels:
    block = all_blocks.get(parcel.block, None)
    if block is None:
        block = BlockDatum(parcel.block)
        all_blocks[parcel.block] = block
    block.sample_parcel(parcel)

# Now that we can extrapolate land values from the block samples, we can
# process all parcels again.
for parcel in all_parcels:
    block = all_blocks.get(parcel.block, None)
    if block is None:
        block = BlockDatum(parcel.block)
        all_blocks[parcel.block] = block
    block.add_parcel(parcel)

sampled_blocks = [b for b in all_blocks.values() if b.is_sampled]

print('Num Blocks:        ', len(all_blocks))
print('Num Sample Blocks: ', len(sampled_blocks))

def sqft_to_sqmi(sqft):
    return sqft * 3.58701e-8

total_land_area_in_sqft = sum(b.total_land_area for b in sampled_blocks)
total_land_area_in_sqmi = sqft_to_sqmi(total_land_area_in_sqft)

avg_sample_block_value_growth = sum(((b.total_land_area/total_land_area_in_sqft) * (b.total_extrapolated_land_value/b.total_assessed_land_value)) for b in sampled_blocks)
print('Average Sample Block Land Value Growth: ', avg_sample_block_value_growth)

total_assessed_land_value = sum(b.total_assessed_land_value for b in sampled_blocks)
total_extrapolated_land_value = sum(b.total_extrapolated_land_value for b in sampled_blocks)

blocks_by_assessed_value = sorted(sampled_blocks, key=lambda b: b.avg_assessed_land_value_per_area())
blocks_by_extrapolated_value = sorted(sampled_blocks, key=lambda b: b.avg_extrapolated_land_value_per_area())

avg_assessed_land_value_per_area = weighted_average(blocks_by_assessed_value, lambda b: b.total_land_area, lambda b: b.avg_assessed_land_value_per_area())

avg_extrapolated_land_value_per_area = weighted_average(blocks_by_extrapolated_value, lambda b: b.total_land_area, lambda b: b.avg_extrapolated_land_value_per_area())

assessed_per_sqft_pctl = []
for i in range(0, 101):
    assessed_per_sqft_pctl.append(weighted_percentile(blocks_by_assessed_value, lambda b: b.total_land_area, lambda b: b.avg_assessed_land_value_per_area(), 0.01*i))

extrapolated_per_sqft_pctl = []
for i in range(0, 101):
    extrapolated_per_sqft_pctl.append(weighted_percentile(blocks_by_extrapolated_value, lambda b: b.total_land_area, lambda b: b.avg_extrapolated_land_value_per_area(), 0.01*i))

print('Average Assessed Land Value Per Square Foot:     ', avg_assessed_land_value_per_area)
print('Average Extrapolated Land Value Per Square Foot: ', avg_extrapolated_land_value_per_area)

print('Total Assessed Land Area in Square Feet:  ', total_land_area_in_sqft)
print('Total Assessed Land Area in Square Miles: ', total_land_area_in_sqmi)

print('Total Assessed Land Value:     ', total_assessed_land_value)
print('Total Extrapolated Land Value: ', total_extrapolated_land_value)

print('Median Assessed Land Value Per Square Foot:     ', assessed_per_sqft_pctl[50])
print('Median Extrapolated Land Value Per Square Foot: ', extrapolated_per_sqft_pctl[50])

def print_csv_data():
    print('\n\nPercentile Area,Assessed Per Square Foot,Extrapolated Per Square Foot')
    for i in range(0, 101):
        print('{},{},{}'.format(i, assessed_per_sqft_pctl[i], extrapolated_per_sqft_pctl[i]))





