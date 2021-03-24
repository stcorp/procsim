#!/bin/sh

# Stop on first error
set -e

# Unit tests
cd procsim
python3 -m unittest

# Test help/version info
python3 procsim.py -v
python3 procsim.py -h
python3 procsim.py -h biomass S1_RAW__0S

# System tests
cd ..
test/test.sh
