#!/bin/sh
#-----------------------------------------------------------
# Test processor stubs using PVML.
# 
# NB: Call from workspace root!
#-----------------------------------------------------------

# exit when any command fails
set -e

# Generate test data
mkdir -p data/raw
python3 procsim/procsim.py -s "Raw data generator" test/procsim_config.json

# Generate aux data
mkdir -p data/AUX_CN0_AX
echo test > data/AUX_CN0_AX/AUX_CN0_AXVIEC20030723_000000_19910101_000000_20101231_235959

# Create workspace root
mkdir -p workspace

# --------------------------------
# Run test jobs.
# --------------------------------

# Step1: Create RAWS_023,024,025,026 products (TODO: All 9 products?)
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1.xml

# Step2 and 3: Create Sx_RAW__0S and Sx_RAW__0M products (Measurement mode)
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2.xml
