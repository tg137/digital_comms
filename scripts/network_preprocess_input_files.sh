#!/bin/bash
. /opt/miniconda/etc/profile.d/conda.sh
conda activate digital_comms

#cd /soge-home/projects/mistral/nismod/digital_comms
mkdir -p /soge-home/projects/mistral/nismod/digital_comms/data/intermediate/intermediate_exchanges/$1
touch /soge-home/projects/mistral/nismod/digital_comms/data/intermediate/intermediate_exchanges/$1/log.txt

python $(dirname $0)/network_preprocess_input_files.py $1  'False' &> \
/soge-home/projects/mistral/nismod/digital_comms/data/intermediate/intermediate_exchanges/$1/log.txt

# # source activate digital_comms
# cd /soge-home/projects/mistral/nismod/digital_comms/



# python `pwd`/scripts/network_preprocess_input_files.py $1 &> /soge-home/projects/mistral/nismod/digital_comms/data/digital_comms/intermediate/intermediate_exchanges/$1/log.txt
