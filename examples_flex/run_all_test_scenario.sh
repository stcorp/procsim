#!/bin/bash
#--------------------------------------------------------------------------
# ESA procsim TEST Scenario.
#--------------------------------------------------------------------------

# Exit when any command fails
set -e

# Catch command line argument '--no-wait'
if [ "$1" == "--no-wait" ]; then
  no_wait=true
else
  no_wait=false
fi

# If the command line argument '--no-wait' is given, the script will not wait for a keypress.
wait_for_keypress() {
  echo "arg=$no_wait"
  if [ "$no_wait" = false ]; then
    read -s -n 1
  fi
}


# Create clean workspace
# Check if any of the directories exist
if [ -d "RAW_output" ] || [ -d "L0Step1_output" ] || [ -d "L0Step2_output" ] || [ -d "L0Step3_output" ]; then

  # Set the backup folder name
  backup_folder="bck_$(date +%Y%m%d_%H%M%S)"

  # Create the backup folder and move the directories into it
  mkdir "$backup_folder"

  if [ -d "RAW_output" ]; then
    mv RAW_output "$backup_folder"
  fi

  if [ -d "L0Step1_output" ]; then
    mv L0Step1_output "$backup_folder"
  fi

  if [ -d "L0Step2_output" ]; then
    mv L0Step2_output "$backup_folder"
  fi

  if [ -d "L0Step3_output" ]; then
    mv L0Step3_output "$backup_folder"
  fi
fi

mkdir RAW_output
mkdir L0Step1_output
mkdir L0Step2_output
mkdir L0Step3_output

# Generate raw data
echo ' '
echo '  ************************************ Generate raw data ************************************ '
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' procsim -s "Raw data generator: DATA-DUMP 1" procsim_config_raw.json'
wait_for_keypress
echo '  ************************************ Generate raw data for EO DATA-DUMP 1  --> '
procsim -s "Raw data generator: DATA-DUMP 1" procsim_config_raw.json
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' procsim -s "Raw data generator: DATA-DUMP 2" procsim_config_raw.json'
wait_for_keypress
echo '  ************************************ Generate raw data for EO DATA-DUMP 2  --> '
procsim -s "Raw data generator: DATA-DUMP 2" procsim_config_raw.json
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' procsim -s "Raw data generator: DATA-DUMP 3" procsim_config_raw.json'
wait_for_keypress
echo '  ************************************ Generate raw data for CAL DATA-DUMP  --> '
procsim -s "Raw data generator: DATA-DUMP 3" procsim_config_raw.json
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' procsim -s "Raw data generator: DATA-DUMP 4" procsim_config_raw.json'
wait_for_keypress
echo '  ************************************ Generate raw data for CAL DATA-DUMP  --> '
procsim -s "Raw data generator: DATA-DUMP 4" procsim_config_raw.json
echo ' '
echo ' '
echo '  ************************************ GENERATED RAW DATA:  ************************************ '
ls -lrt RAW_output
echo ' '
echo ' '
echo ' '
echo '  ************************************ L0 STEP 1 ************************************ '
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with L0 STEP 1'
echo ' L0 STEP 1: RAW HR1 DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR1_D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR1 DATA DUMP 1 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-HR1_D1.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 1: RAW HR2 DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR2_D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR2 DATA DUMP 1 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-HR2_D1.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 1: RAW LR DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-LR__D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW LR DATA DUMP 1 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-LR__D1.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 1: RAW HR1 DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR1_D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR1 DATA DUMP 2 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-HR1_D2.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 1: RAW HR2 DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR2_D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR2 DATA DUMP 2 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-HR2_D2.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 1: RAW LR DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-LR__D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW LR DATA DUMP 2 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-LR__D2.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with: WARNING NEVER TRIED BEFORE!!!'
echo ' L0 STEP 1: RAW OBC DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-OBC_D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW OBC DATA DUMP 1 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-OBC_D1.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 1: RAW OBC DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-LR__D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW OBC DATA DUMP 2 --> '
./level0_step1.sh Scenario1_EO/JobOrder.L0PF_S1_RAW-OBC_D2.xml
echo ' '
echo ' '
echo ' '
echo '  ************************************ L0 STEP 2 ************************************ '
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with L0 STEP 2'
echo ' L0 STEP 2: HR2 Slice 3 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-HR2-Slice3.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: HR2 Slice 3 --> '
./level0_step2.sh Scenario1_EO/JobOrder.L0PF_S2_RWS-HR2-Slice3.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 2: HR1 Slice 7 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-HR1-Slice7.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: HR1 Slice 7  --> '
./level0_step2.sh Scenario1_EO/JobOrder.L0PF_S2_RWS-HR1-Slice7.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 2: HR2 VAU - orbit 1024 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-HR2-VAU-1024.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: HR2 VAU - orbit 1024  --> '
./level0_step2.sh Scenario1_EO/JobOrder.L0PF_S2_RWS-HR2-VAU-1024.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 2: LR VAU - orbit 1024 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-LR_-VAU-1024.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: LR VAU - orbit 1024  --> '
./level0_step2.sh Scenario1_EO/JobOrder.L0PF_S2_RWS-LR_-VAU-1024.xml
echo ' '
echo ' '
echo ' '
echo '  ************************************ L0 STEP 3 ************************************ '
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with L0 STEP 3'
echo ' L0 STEP 3: Slice 1 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 1 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-1.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 2 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 2 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-2.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 3 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-3.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 3 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-3.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 4 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-4.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 4 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-4.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 5 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-5.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 5 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-5.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 6 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-6.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 6 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-6.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 7 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-7.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 7 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-7.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 8 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-8.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 8 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-8.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: Slice 9 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-9.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 9 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-9.xml
echo ' '
echo ' '
echo ' ---------> PRESS a button to continue with:'
echo ' L0 STEP 3: VAU orbit 1024 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-VAU-1024.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice VAU - orbit 1024 --> '
./level0_step3.sh Scenario1_EO/JobOrder.L0PF_S3_RWS-VAU-1024.xml
