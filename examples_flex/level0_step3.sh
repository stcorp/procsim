#!/bin/sh

# Exit when any command fails
set -e

# Combine complete sensor data to generate L0 products
echo
echo '  *** L0 step 3, job order '$1
procsim -t level0_task3.sh -j $1 procsim_config_l0_step3.json --no-match-outputs
