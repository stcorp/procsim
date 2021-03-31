#!/bin/sh

# Stop on first error
set -e

# Unit tests
python3 -m unittest discover

# Test help/version info
python3 procsim -v
python3 procsim -h
python3 procsim -h biomass S1_RAW__0S

# System tests
test/test.sh
