#!/bin/sh
#-----------------------------------------------------------
# Test processor stubs using PVML.
# 
# NB: Call from workspace root!
#-----------------------------------------------------------

# Generate test data
mkdir -p data/AUX_CN0_AX
echo test > data/AUX_CN0_AX/AUX_CN0_AXVIEC20030723_000000_19910101_000000_20101231_235959
mkdir -p data/raw
python tasksim/biomass/raw_generator.py data/raw

# Create workspace root
mkdir workspace

# Run test job
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0.xml
