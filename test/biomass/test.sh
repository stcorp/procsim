#!/bin/sh
#-------------------------------------------------------------------
# Test Biomass processor stubs by generating a chain of products,
# from raw and aux data up to level 2a.
# To run the script, an external 'Processor Management Layer' must
# be available on the test system.
#
# NB: Call this script from the project's root!
#-------------------------------------------------------------------

# Exit when any command fails
set -e

PVML_CMD=$1

# Clean up
rm -rf data
rm -rf workspace

# Create workspace root
mkdir -p workspace


# --------------------------------
# Run test jobs.
# --------------------------------

echo '  *** Generate aux data'
mkdir -p data
procsim -s "Aux generator" test/biomass/procsim_aux_scenario.json

# Generate test data
echo
echo
echo '  *** Generate raw data (measurement mode)'
mkdir -p data
procsim -s "Raw data generator, measurement mode" test/biomass/procsim_config.json

# Level 0 steps
echo
echo '  *** L0 step 1a first datatake (measurement mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step1a_sm.xml
echo
echo '  *** L0 step 1b second datatake (measurement mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step1b_sm.xml

echo
echo '  *** L0 step 2, 3, 4 complete slice (measurement mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step2a_sm.xml
echo
echo '  *** L0 step 2, 3, 4 incomplete (first) slice (measurement mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step2b_sm.xml
echo
echo '  *** L0 step 2, 3, 4 split slice (measurement mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step2c_sm.xml

# Level 1 steps
echo
echo '  *** L1 step 1a, slice preprocessing'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l1_pp.xml
echo '  *** L1 step 1b, input complete slice'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l1_sm.xml

echo
echo '  *** L1 step 2'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l1_stack.xml

# Level 2 steps
echo
echo '  *** L2a'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l2a.xml


# --------------------------------
# RO mode
# --------------------------------

echo
echo
echo '  *** Generate raw data (ro mode)'
mkdir -p data/raw_ec
procsim -s "Raw data generator, ro mode" test/biomass/procsim_config.json

# Level 0 steps
echo
echo '  *** L0 step 1a (ro mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step1a_ro.xml
echo
echo '  *** L0 step 1b (ro mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step1b_ro.xml

echo
echo '  *** L0 step 2, 3, 4 (ro mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step2a_ro.xml

# --------------------------------
# EC mode
# --------------------------------

# Generate test data
echo
echo
echo
echo '  *** Generate raw data (ec mode)'
mkdir -p data/raw_ec
procsim -s "Raw data generator, ec mode" test/biomass/procsim_config.json

# Level 0 steps
echo
echo '  *** L0 step 1 (ec mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step1a_ec.xml

echo
echo '  *** L0 step 2, 3, 4, 5 (ec mode)'
$PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step2a_ec.xml


# Check whether MPH contents and folder contents correspond.
python3 -c 'import procsim.biomass.test.test_main_product_header as testmph; testmph.assertMPHMatchesProductRecursive("workspace/");'
