import os
from pprint import pprint
import configparser
import csv

### csv import postcode data
    # 2016 and 2017 are individual csv files for each two digit postcode
    # 2014 and 2015 are single csv files containing all pcds

### select desired variables
    # 2017
        # 'postcode'
        # 'SFBB availability (% premises)'
        # 'UFBB availability (% premises)'
    # 2016
        # 'postcode'
        # 'SFBB availability (% premises)'
        # 'UFBB availability (% premises)'
    # 2015
        # 'postcode'
        # 'SFBB availability by PC (% premises)'
        # 'UFBB availability by PC (% premises)'
    # 2014
        # 'postcode'
        # 'SFBB (>30 Mbit/s) availability by PC (% premises)'

### divide % premises variable by 100 to obtain factor

### import codepoint postcode data

### multiply for each postcode by codepoint premises numbers?

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

SYSTEM_INPUT_FILENAME = os.path.join(BASE_PATH, 'Digital Comms - Fixed broadband model', 'Data', 'initial_system')

SYSTEM_OUTPUT_FILENAME = os.path.join(BASE_PATH, 'Digital Comms - Fixed broadband model', 'initial_system')

initial_system = []

YEARS = ['2016', '2017']

#####################
# read in files for 2016 and 2017
#####################

for year in YEARS:
    for fixed_pcd_file in os.listdir(SYSTEM_INPUT_FILENAME):
        if fixed_pcd_file.startswith(year):
            with open(os.path.join(SYSTEM_INPUT_FILENAME, fixed_pcd_file), 'r') as system_file:
                reader = csv.reader(system_file)
                next(reader)  # skip header
                for line in reader:
                    initial_system.append({
                        'postcode': line[0],
                        'SFBB': line[3],
                        'UFBB': line[4]
                    })

# write files for 2016 and 2017
            with open(os.path.join(SYSTEM_OUTPUT_FILENAME, 'fixed_postcode_' + str(year) + '.csv'), 'w', newline='') as output_file:
                output_writer = csv.writer(output_file)

                # Write header
                output_writer.writerow(("postcode", "SFBB", "UFBB"))

                # Write data
                for pcd in initial_system:
                    # so by using a for loop, we're accessing each element in the list.
                    # each postcode is then a dict, so we need to index into each dict item
                    postcode = pcd['postcode']
                    SFBB = pcd['SFBB']
                    UFBB = pcd['UFBB']

                    output_writer.writerow(
                        (postcode, SFBB, UFBB))

            output_file.close()

#####################
# read files for 2015
#####################

with open(os.path.join(SYSTEM_INPUT_FILENAME, 'Fixed_Postcode_2015_updated_01022016.csv'), 'r') as system_file:
                reader = csv.reader(system_file)
                next(reader)  # skip header
                for line in reader:
                    initial_system.append({
                        'postcode': line[0],
                        'SFBB': line[2],
                        'UFBB': line[3],
                    })

with open(os.path.join(SYSTEM_OUTPUT_FILENAME, 'fixed_postcode_2015.csv'), 'w', newline='') as output_file:
    output_writer = csv.writer(output_file)

    # Write header
    output_writer.writerow(("postcode", "SFBB", "UFBB"))

    # Write data
    for pcd in initial_system:
        # so by using a for loop, we're accessing each element in the list.
        # each postcode is then a dict, so we need to index into each dict item
        postcode = pcd['postcode']
        SFBB = pcd['SFBB']
        UFBB = pcd['UFBB']              # <- there is no UFBB column for 2014 so calibrate as zero

        output_writer.writerow(
            (postcode, SFBB, UFBB))

output_file.close()

#####################
# read files for 2014
#####################

with open(os.path.join(SYSTEM_INPUT_FILENAME, 'fixed_postcode_2014_CB.csv'), 'r') as system_file:
                reader = csv.reader(system_file)
                next(reader)  # skip header
                for line in reader:
                    initial_system.append({
                        'postcode': line[0],
                        'SFBB': line[2],
                    })

with open(os.path.join(SYSTEM_OUTPUT_FILENAME, 'fixed_postcode_2014.csv'), 'w', newline='') as output_file:
    output_writer = csv.writer(output_file)

    # Write header
    output_writer.writerow(("postcode", "SFBB", "UFBB"))

    # Write data
    for pcd in initial_system:
        # so by using a for loop, we're accessing each element in the list.
        # each postcode is then a dict, so we need to index into each dict item
        postcode = pcd['postcode']
        SFBB = pcd['SFBB']
        UFBB = 0              # <- there is no UFBB column for 2014 so calibrate as zero

        output_writer.writerow(
            (postcode, SFBB, UFBB))

output_file.close()

