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
mkdir -p data
python3 procsim/procsim.py -s "Raw data generator, measurement mode" test/procsim_config.json

# Level 0 steps
echo '  *** L0 step 1a first datatake (measurement mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1a_sm.xml
echo '  *** L0 step 1b second datatake (measurement mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1b_sm.xml

echo '  *** L0 step 2, 3, 4 complete slice (measurement mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2a_sm.xml
echo '  *** L0 step 2, 3, 4 incomplete (first) slice (measurement mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2b_sm.xml
echo '  *** L0 step 2, 3, 4 split slice (measurement mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2c_sm.xml

# --------------------------------
# RO mode
# --------------------------------

# Generate test data
echo
echo '  *** Generate raw data (ro mode)'
mkdir -p data/raw_ec
python3 procsim/procsim.py -s "Raw data generator, ro mode" test/procsim_config.json

# Level 0 steps
echo '  *** L0 step 1a (ro mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1a_ro.xml
echo '  *** L0 step 1b (ro mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1b_ro.xml

echo '  *** L0 step 2, 3, 4 (ro mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2a_ro.xml

# --------------------------------
# EC mode
# --------------------------------

# Generate test data
echo
echo '  *** Generate raw data (ec mode)'
mkdir -p data/raw_ec
python3 procsim/procsim.py -s "Raw data generator, ec mode" test/procsim_config.json

# Level 0 steps
echo '  *** L0 step 1 (ec mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step1a_ec.xml

echo '  *** L0 step 2, 3, 4, 5 (ec mode)'
python3 pvml/pvml.py test/pvml_config.xml test/pvml_job_biomass_l0_step2a_ec.xml
