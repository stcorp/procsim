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

# Combine complete sensor data to generate L0 products
echo
echo '  *** L0 step 3'
procsim -t level0_task3.sh -j $1 procsim_config_l0_step3.json --no-match-outputs
echo
