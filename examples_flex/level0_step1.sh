#!/bin/sh

# Exit when any command fails
set -e

# Generate sliced raw data
echo
echo '  *** L0 step 1, job order '$1
procsim -t level0_task1.sh -j $1 procsim_config_l0_step1.json --no-match-outputs
