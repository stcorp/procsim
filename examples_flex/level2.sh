#!/bin/sh

# Exit when any command fails
set -e

# Generate L1 products
echo
echo '  *** L2, job order '$1
procsim -t level2_task1.sh -j $1 procsim_config_l2.json --no-match-outputs
