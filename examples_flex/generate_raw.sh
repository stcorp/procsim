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
echo '  *** Generate raw data (measurement mode)'
procsim -s "Raw data generator, measurement mode" procsim_config_raw.json
