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
echo

WORKSPACE_1=workspace/1
mkdir -p $WORKSPACE_1
cp data/raw_sm/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip $WORKSPACE_1
cp data/raw_sm/BIO_RAW_023_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip $WORKSPACE_1
cp data/raw_sm/BIO_RAW_024_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip $WORKSPACE_1
cp data/raw_sm/BIO_RAW_025_10_20210201T002432_20210201T002932_D20210201T013810_01_B07CK0.zip $WORKSPACE_1
cp data/raw_sm/BIO_RAW_026_10_20210201T002432_20210201T002932_D20210201T013810_01_B07CK0.zip $WORKSPACE_1
cp test/biomass/joborders/JobOrder.1.xml $WORKSPACE_1
cd $WORKSPACE_1
../../test/biomass/level0_task1.sh JobOrder.1.xml
cd -

echo
echo '  *** L0 step 1b second datatake (measurement mode)'
echo

WORKSPACE_2=workspace/2
mkdir -p $WORKSPACE_2
cp data/raw_sm/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip $WORKSPACE_2
cp data/raw_sm/BIO_RAW_023_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip $WORKSPACE_2
cp data/raw_sm/BIO_RAW_024_10_20210201T000000_20210201T013810_D20210201T013810_01_B07CK0.zip $WORKSPACE_2
cp data/raw_sm/BIO_RAW_025_10_20210201T003432_20210201T003932_D20210201T013810_01_B07CK0.zip $WORKSPACE_2
cp data/raw_sm/BIO_RAW_026_10_20210201T003432_20210201T003932_D20210201T013810_01_B07CK0.zip $WORKSPACE_2
cp test/biomass/joborders/JobOrder.2.xml $WORKSPACE_2
cd $WORKSPACE_2
../../test/biomass/level0_task1.sh ./JobOrder.2.xml
cd -

echo
echo '  *** L0 step 2, 3, 4 complete slice (measurement mode)'
echo
WORKSPACE_1000=workspace/1000
mkdir -p $WORKSPACE_1000

cp $WORKSPACE_1/BIO_RAWS025_10_20210201T002528_20210201T002715_D20210201T013810_00_??????.zip $WORKSPACE_1000
cp $WORKSPACE_1/BIO_RAWS026_10_20210201T002528_20210201T002715_D20210201T013810_00_??????.zip $WORKSPACE_1000
cp $WORKSPACE_1/BIO_RAWS023_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1000
cp $WORKSPACE_1/BIO_RAWS024_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1000
cp $WORKSPACE_1/BIO_RAWS022_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1000
cp test/biomass/joborders/JobOrder.1000.xml $WORKSPACE_1000
cd $WORKSPACE_1000
ls -l
../../test/biomass/level0_task2.sh ./JobOrder.1000.xml
../../test/biomass/level0_task3.sh ./JobOrder.1000.xml
../../test/biomass/level0_task4.sh ./JobOrder.1000.xml
../../test/biomass/level0_task6.sh ./JobOrder.1000.xml
cd -

echo
echo '  *** L0 step 2, 3, 4 incomplete (first) slice (measurement mode)'
echo
WORKSPACE_1001=workspace/1001
mkdir -p $WORKSPACE_1001
cp $WORKSPACE_1/BIO_RAWS025_10_20210201T002432_20210201T002539_D20210201T013810_00_??????.zip $WORKSPACE_1001
cp $WORKSPACE_1/BIO_RAWS026_10_20210201T002432_20210201T002539_D20210201T013810_00_??????.zip $WORKSPACE_1001
cp $WORKSPACE_1/BIO_RAWS023_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1001
cp $WORKSPACE_1/BIO_RAWS024_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1001
cp $WORKSPACE_1/BIO_RAWS022_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1001
cp test/biomass/joborders/JobOrder.1001.xml $WORKSPACE_1001
cd $WORKSPACE_1001
../../test/biomass/level0_task2.sh ./JobOrder.1001.xml
../../test/biomass/level0_task3.sh ./JobOrder.1001.xml
../../test/biomass/level0_task4.sh ./JobOrder.1001.xml
../../test/biomass/level0_task6.sh ./JobOrder.1001.xml
cd -

echo
echo '  *** L0 step 2, 3, 4 split slice (measurement mode)'
echo
WORKSPACE_1002=workspace/1002
mkdir -p $WORKSPACE_1002
cp $WORKSPACE_2/BIO_RAWS025_10_20210201T003458_20210201T003645_D20210201T013810_00_??????.zip $WORKSPACE_1002
cp $WORKSPACE_2/BIO_RAWS026_10_20210201T003458_20210201T003645_D20210201T013810_00_??????.zip $WORKSPACE_1002
cp $WORKSPACE_2/BIO_RAWS023_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1002
cp $WORKSPACE_2/BIO_RAWS024_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1002
cp $WORKSPACE_2/BIO_RAWS022_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE_1002
cp test/biomass/joborders/JobOrder.1002.xml $WORKSPACE_1002
cd $WORKSPACE_1002
../../test/biomass/level0_task2.sh ./JobOrder.1002.xml
../../test/biomass/level0_task3.sh ./JobOrder.1002.xml
../../test/biomass/level0_task4.sh ./JobOrder.1002.xml
../../test/biomass/level0_task6.sh ./JobOrder.1002.xml
cd -

# Level 1 steps
echo
echo '  *** L1 step 1, slice preprocessing'
echo
WORKSPACE_2000=workspace/2000
mkdir -p $WORKSPACE_2000
cp -r $WORKSPACE_1000/BIO_S1_RAW__0S_20210201T002528_20210201T002715_T_G___M01_C___T000_F001_00_?????? $WORKSPACE_2000
cp -r $WORKSPACE_1000/BIO_S1_RAW__0M_20210201T002528_20210201T002715_T_G___M01_C___T000_F____00_?????? $WORKSPACE_2000
cp -r $WORKSPACE_1000/BIO_AUX_ORB____20210201T002512_20210201T002715_00_?????? $WORKSPACE_2000
cp test/biomass/joborders/JobOrder.2000.xml $WORKSPACE_2000
cd $WORKSPACE_2000
../../test/biomass/level1_task1.sh ./JobOrder.2000.xml
cd -

echo
echo '  *** L1 step 2, input complete slice'
echo
WORKSPACE_2010=workspace/2010
mkdir -p $WORKSPACE_2010
cp -r $WORKSPACE_2000/BIO_TEST_CPF_L1VFRA_20210201T002533_20210201T002554_00_??????.EOF $WORKSPACE_2010
cp -r $WORKSPACE_1000/BIO_S1_RAW__0S_20210201T002528_20210201T002715_T_G___M01_C___T000_F001_00_?????? $WORKSPACE_2010
cp -r $WORKSPACE_1000/BIO_S1_RAW__0M_20210201T002528_20210201T002715_T_G___M01_C___T000_F____00_?????? $WORKSPACE_2010
cp -r $WORKSPACE_1000/BIO_AUX_ATT____20210201T002512_20210201T002715_00_?????? $WORKSPACE_2010
cp -r $WORKSPACE_1000/BIO_AUX_ORB____20210201T002512_20210201T002715_00_?????? $WORKSPACE_2010
cp -r data/aux/BIO_AUX_INS____20210201T000000_20210201T013810_01_?????? $WORKSPACE_2010
cp -r data/aux/BIO_AUX_PP1____20210201T000000_20210201T013810_01_?????? $WORKSPACE_2010
cp -r data/aux/BIO_AUX_TEC____20210201T000000_20210201T013810_01_?????? $WORKSPACE_2010
cp -r data/aux/BIO_AUX_GMF____20210201T000000_20210201T013810_01_?????? $WORKSPACE_2010
cp test/biomass/joborders/JobOrder.2010.xml $WORKSPACE_2010
cd $WORKSPACE_2010
../../test/biomass/level1_task2.sh ./JobOrder.2010.xml
cd -

echo
echo '  *** L1 step 3'
echo
WORKSPACE_3000=workspace/3000
mkdir -p $WORKSPACE_3000
cp -r $WORKSPACE_2010/BIO_S1_SCS__1S_20210201T002533_20210201T002554_T_G___M01_C01_T000_F001_00_?????? $WORKSPACE_3000
cp -r $WORKSPACE_2010/BIO_S1_SCS__1S_20210201T002533_20210201T002554_T_G___M01_C02_T000_F001_00_?????? $WORKSPACE_3000
cp -r $WORKSPACE_2010/BIO_S1_SCS__1S_20210201T002533_20210201T002554_T_G___M01_C03_T000_F001_00_?????? $WORKSPACE_3000
cp -r data/aux/BIO_AUX_PPS____20210201T000000_20210201T013810_01_?????? $WORKSPACE_3000
cp test/biomass/joborders/JobOrder.3000.xml $WORKSPACE_3000
cd $WORKSPACE_3000
../../test/biomass/level1_task3.sh ./JobOrder.3000.xml
cd -

# Level 2 steps
echo
echo '  *** L2a interferometric'
echo
WORKSPACE_4000=workspace/4000
mkdir -p $WORKSPACE_4000
cp -r $WORKSPACE_3000/BIO_S1_STA__1S_20210201T002533_20210201T002554_T_G___M01_C01_T000_F001_00_?????? $WORKSPACE_4000
cp -r $WORKSPACE_3000/BIO_S1_STA__1S_20210201T002533_20210201T002554_T_G___M01_C02_T000_F001_00_?????? $WORKSPACE_4000
cp -r $WORKSPACE_3000/BIO_S1_STA__1S_20210201T002533_20210201T002554_T_G___M01_C03_T000_F001_00_?????? $WORKSPACE_4000
cp -r data/aux/BIO_AUX_PP2_2A_20210201T000000_20210201T013810_01_?????? $WORKSPACE_4000
cp test/biomass/joborders/JobOrder.4000.xml $WORKSPACE_4000
cd $WORKSPACE_4000
../../test/biomass/level2a_task1.sh ./JobOrder.4000.xml
cd -

echo
echo '  *** L2a tomographic'
echo
WORKSPACE_4010=workspace/4010
mkdir -p $WORKSPACE_4010
cp -r $WORKSPACE_3000/BIO_S1_STA__1S_20210201T002533_20210201T002554_T_G___M01_C01_T000_F001_00_?????? $WORKSPACE_4010
cp -r $WORKSPACE_3000/BIO_S1_STA__1S_20210201T002533_20210201T002554_T_G___M01_C02_T000_F001_00_?????? $WORKSPACE_4010
cp -r $WORKSPACE_3000/BIO_S1_STA__1S_20210201T002533_20210201T002554_T_G___M01_C03_T000_F001_00_?????? $WORKSPACE_4010
cp -r data/aux/BIO_AUX_PP2_2A_20210201T000000_20210201T013810_01_?????? $WORKSPACE_4010
cp test/biomass/joborders/JobOrder.4010.xml $WORKSPACE_4010
cd $WORKSPACE_4010
../../test/biomass/level2a_task1.sh ./JobOrder.4010.xml
cd -

# --------------------------------
# RO mode
# --------------------------------

echo
echo
echo '  *** Generate raw data (ro mode)'
echo
mkdir -p data/raw_ec
procsim -s "Raw data generator, ro mode" test/biomass/procsim_config.json

# Level 0 steps
echo
echo '  *** L0 step 1a (ro mode)'
echo
WORKSPACE_20=workspace/20
mkdir -p $WORKSPACE_20
cp data/raw_ro/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013810_01_??????.zip $WORKSPACE_20
cp data/raw_ro/BIO_RAW_023_10_20210201T000000_20210201T013810_D20210201T013810_01_??????.zip $WORKSPACE_20
cp data/raw_ro/BIO_RAW_024_10_20210201T000000_20210201T013810_D20210201T013810_01_??????.zip $WORKSPACE_20
cp data/raw_ro/BIO_RAW_027_10_20210201T002432_20210201T002932_D20210201T013810_01_??????.zip $WORKSPACE_20
cp data/raw_ro/BIO_RAW_028_10_20210201T002432_20210201T002932_D20210201T013810_01_??????.zip $WORKSPACE_20
cp test/biomass/joborders/JobOrder.20.xml $WORKSPACE_20
cd $WORKSPACE_20
../../test/biomass/level0_task1.sh ./JobOrder.20.xml
cd -
# $PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step1a_ro.xml

echo
echo '  *** L0 step 1b (ro mode)'
echo
WORKSPACE_21=workspace/21
mkdir -p $WORKSPACE_21
cp data/raw_ro/BIO_RAW_022_10_20210201T000000_20210201T013810_D20210201T013810_01_??????.zip $WORKSPACE_21
cp data/raw_ro/BIO_RAW_023_10_20210201T000000_20210201T013810_D20210201T013810_01_??????.zip $WORKSPACE_21
cp data/raw_ro/BIO_RAW_024_10_20210201T000000_20210201T013810_D20210201T013810_01_??????.zip $WORKSPACE_21
cp data/raw_ro/BIO_RAW_027_10_20210201T003432_20210201T003932_D20210201T013810_01_??????.zip $WORKSPACE_21
cp data/raw_ro/BIO_RAW_028_10_20210201T003432_20210201T003932_D20210201T013810_01_??????.zip $WORKSPACE_21
cp test/biomass/joborders/JobOrder.21.xml $WORKSPACE_21
cd $WORKSPACE_21
../../test/biomass/level0_task1.sh ./JobOrder.21.xml
cd -
# $PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step1b_ro.xml

echo
echo '  *** L0 step 2, 3, 4 (ro mode)'
echo
WORKSPACE1020=workspace/1020
mkdir -p $WORKSPACE1020
cp $WORKSPACE_20/BIO_RAWS027_10_20210201T002528_20210201T002715_D20210201T013810_00_??????.zip $WORKSPACE1020
cp $WORKSPACE_20/BIO_RAWS028_10_20210201T002528_20210201T002715_D20210201T013810_00_??????.zip $WORKSPACE1020
cp $WORKSPACE_20/BIO_RAWS023_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE1020
cp $WORKSPACE_20/BIO_RAWS024_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE1020
cp $WORKSPACE_20/BIO_RAWS022_10_20210201T000000_20210201T013810_D20210201T013810_00_??????.zip $WORKSPACE1020
cp test/biomass/joborders/JobOrder.1020.xml $WORKSPACE1020
cd $WORKSPACE1020
../../test/biomass/level0_task2.sh ./JobOrder.1020.xml
../../test/biomass/level0_task3.sh ./JobOrder.1020.xml
../../test/biomass/level0_task4.sh ./JobOrder.1020.xml
cd -
# $PVML_CMD test/biomass/pvml_config.xml test/biomass/pvml_job_biomass_l0_step2a_ro.xml

exit 0

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
