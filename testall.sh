#!/bin/sh

# Stop on first error
set -e

# Test help/version info
procsim -v
procsim -h
procsim -i S1_RAW__0S

# Unit tests
echo
echo "Run unit tests"
echo
python3 -m unittest discover

# System tests
echo
echo "Run Biomass system tests"
echo
test/biomass/test.sh "python3 ../pvml/pvml.py"

# Test examples
echo
echo "Test examples"
echo
cd examples
./generate_aux_data.sh
./generate_L0.sh

echo
echo "All tests ok"
echo