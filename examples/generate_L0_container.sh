#!/bin/sh
#--------------------------------------------------------------------------
# S&T podmanized procsim demo.
#
# - Make sure the procsim container image is available!
# - Replace 'podman' by 'docker' to use docker.
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
podman run --rm -v $PWD/:/app/:Z procsim -s "Raw data generator, measurement mode" procsim_config.json

# Generate sliced raw data
echo
echo '  *** L0 step 1'
python3 resolve_wildcards.py JobOrder_template.1.xml JobOrder.1.xml
podman run --rm -v $PWD/:/app/:Z procsim -t level0_task1.sh -j JobOrder.1.xml procsim_config.json
echo
echo '  *** L0 step 2'
python3 resolve_wildcards.py JobOrder_template.2.xml JobOrder.2.xml
podman run --rm -v $PWD/:/app/:Z procsim -t level0_task2.sh -j JobOrder.2.xml procsim_config.json
echo
echo '  *** L0 step 3'
python3 resolve_wildcards.py JobOrder_template.2.xml JobOrder.2.xml
podman run --rm -v $PWD/:/app/:Z procsim -t level0_task3.sh -j JobOrder.2.xml procsim_config.json
echo
echo '  *** L0 step 4'
python3 resolve_wildcards.py JobOrder_template.2.xml JobOrder.2.xml
podman run --rm -v $PWD/:/app/:Z procsim -t level0_task4.sh -j JobOrder.2.xml procsim_config.json
