#!/bin/sh
#-----------------------------------------------------------
# Test processor stubs using PVML.
# 
# NB: Call from workspace root!
#-----------------------------------------------------------

# Exit when any command fails
set -e

# Clean up
rm -rf data
rm -rf workspace

# Create workspace root
mkdir -p workspace


# --------------------------------
# Run test jobs.
# --------------------------------

# Generate test data
echo '  *** Generate raw data (measurement mode)'
mkdir -p data/raw
python3 procsim/procsim.py -s "Raw data generator, measurement mode" test/procsim_config.json

# Step1: Create RAWS_023,024,025,026 products (TODO: All 9 products?)
echo '  *** L0 step 1a (measurement mode)'
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1a_sm.xml
echo '  *** L0 step 1b (measurement mode)'
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1b_sm.xml

# Step2 and 3: Create Sx_RAW__0S and Sx_RAW__0M products (Measurement mode)
echo '  *** L0 step 2, 3, 4 (measurement mode)'
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2a_sm.xml
echo '  *** L0 step 2, 3, 4 incomplete slice (measurement mode)'
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2b_sm.xml
echo '  *** L0 step 2, 3, 4 split slice (measurement mode)'
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2c_sm.xml

# --------------------------------
# EC mode
# --------------------------------

# Generate test data
echo
echo '  *** Generate raw data (ec mode)'
mkdir -p data/raw_ec
python3 procsim/procsim.py -s "Raw data generator, ec mode" test/procsim_config.json

# Step1: Create RAWS_023,024,025,026 products (TODO: All 9 products?)
echo '  *** L0 step 1 (ec mode)'
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1a_ec.xml
# echo '  *** L0 step 1b'
# python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1b_ec.xml

# Step2 and 3: Create Sx_RAW__0S and Sx_RAW__0M products (Measurement mode)
echo '  *** L0 step 2, 3, 4, 5 (ec mode)'
python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2a_ec.xml
# echo '  *** L0 step 2,3 incomplete slice'
# python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2b.xml
# echo '  *** L0 step 2,3 split slice'
# python pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2c.xml
