#!/bin/bash
#--------------------------------------------------------------------------
# Generate L1C and L2 using the job orders as provided by ESA
#
# The output is written to the L1_output and L2_output directories
#--------------------------------------------------------------------------

# Exit when any command fails
set -e

echo ' '
echo '  ******************************* L1C  Floris only  ******************************** '
echo ' L1C Slice 0 (FLORIS only) --> ./level1.sh L1C_PF_FLORIS_01.00_24359-24365_20240423T092606_JobOrder'
 ./level1.sh Scenario_L2/L1C_PF_FLORIS_01.00_24359-24365_20240423T092606_JobOrder

echo ' '
echo '  ******************************* L1C ********************************************** '
echo ' L1C Slice 0 --> ./level1.sh L1C_PF_FLXSYN_01.00_24359-24365_20240423T092606_JobOrder'
 ./level1.sh Scenario_L2/L1C_PF_FLXSYN_01.00_24359-24365_20240423T092606_JobOrder

echo ' '
echo '  ******************************* L2 ********************************************** '
echo ' L2 Slice 0 --> ./level2.sh L2_PF_FLORIS_01.00_24359-24365_20240423T092606_JobOrder'
 ./level2.sh Scenario_L2/L2_PF_FLORIS_01.00_24359-24365_20240423T092606_JobOrder
