#!/bin/sh
#-------------------------------------------------------------------
# Test Biomass processor stubs by generating all product types.
#
# NB: Call this script from the project's root!
#-------------------------------------------------------------------

# Exit when any command fails
set -e

# Clean up
rm -rf workspace/all

# Generate
echo
echo '  *** Generate all products'
procsim -s "generate_all" test/flex/procsim_config_generate_all.json
