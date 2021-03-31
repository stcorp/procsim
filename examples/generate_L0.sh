#!/bin/sh
#--------------------------------------------------------------
# S&T procsim demo.
#--------------------------------------------------------------

# Exit when any command fails
set -e

# Create clean workspace
rm -rf workspace
mkdir -p workspace

# Generate raw data
echo '  *** Generate raw data (measurement mode)'
procsim -s "Raw data generator, measurement mode" procsim_config.json

# Generate sliced raw data
echo '  *** L0 step 1'
procsim -t level0_task1.sh -j JobOrder.1.xml procsim_config.json
echo '  *** L0 step 2'
procsim -t level0_task2.sh -j JobOrder.2.xml procsim_config.json
echo '  *** L0 step 3'
procsim -t level0_task3.sh -j JobOrder.2.xml procsim_config.json
echo '  *** L0 step 4'
procsim -t level0_task4.sh -j JobOrder.2.xml procsim_config.json
