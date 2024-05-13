#!/bin/sh

# Exit when any command fails
set -e

# Generate L1 products
echo
echo '  *** L1, job order '$1
procsim -t level1_task1.sh -j $1 procsim_config_l1.json --no-match-outputs
