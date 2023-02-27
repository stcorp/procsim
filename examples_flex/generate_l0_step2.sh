#!/bin/sh
#--------------------------------------------------------------------------
# S&T procsim demo.
#
# The generated files have the creation date in their file name.
# The JobOrder templates have wildcards for the creation date part, the
# 'resolve_wildcards' tool fills in the actual file names.
#--------------------------------------------------------------------------

# Exit when any command fails
set -e

# Create clean workspace
rm -rf workspace
mkdir -p workspace

# Generate raw data
#echo '  *** Generate raw data (measurement mode)'
#procsim -s "Raw data generator, measurement mode" procsim_config_raw.json

# Generate sliced raw data
#echo
#echo '  *** L0 step 1'
#python3 resolve_wildcards.py JobOrder_template.1.xml JobOrder.1.xml
#procsim -t level0_task1.sh -j JobOrder.1.xml procsim_config_l0_step1.json
#echo
echo '  *** L0 step 2'
python3 resolve_wildcards.py JobOrder_template.2.xml JobOrder.2.xml
procsim -t level0_task2.sh -j JobOrder.2.xml procsim_config_l0_step2.json
echo
#echo '  *** L0 step 3'
#python3 resolve_wildcards.py JobOrder_template.3.xml JobOrder.3.xml
#procsim -t level0_task3.sh -j JobOrder.3.xml procsim_config_l0_step3.json
#echo
