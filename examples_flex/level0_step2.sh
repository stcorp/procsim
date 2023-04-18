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

# Merge partial slices
echo
echo '  *** L0 step 2'
procsim -t level0_task2.sh -j $1 procsim_config_l0_step2.json
