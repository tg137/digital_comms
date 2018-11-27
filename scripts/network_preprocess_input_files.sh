#!/bin/bash
. /etc/profile.d/profile.sh
echo Pre-processing $1: Running on `hostname`

source activate digital_comms
cd /ouce-home/projects/mistral/nismod/digital_comms2/

#cd /soge-home/projects/mistral/nismod/digital_comms2
mkdir -p /soge-home/projects/mistral/nismod/digital_comms2/data/digital_comms/intermediate/$1
touch /soge-home/projects/mistral/nismod/digital_comms2/data/digital_comms/intermediate/$1/log.txt

python `pwd`/scripts/network_preprocess_input_files.py $1 &> /soge-home/projects/mistral/nismod/digital_comms2/data/digital_comms/intermediate/$1/log.txt
