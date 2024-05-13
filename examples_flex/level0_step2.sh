#!/bin/sh

# Exit when any command fails
set -e

# Merge partial slices
echo
echo '  *** L0 step 2, job order '$1
procsim -t level0_task2.sh -j $1 procsim_config_l0_step2.json --no-match-outputs
