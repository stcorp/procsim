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
  if [ "$no_wait" = false ]; then
    echo ' '
    echo ' '
    echo ' ---------> PRESS a button to continue'
    read -s -n 1
  fi
}


# Create clean workspace.
# Backup existing directories if they exist, then create fresh directories
directories=("RAW_output" "L0Step1_output" "L0Step2_output" "L0Step3_output" "L1_output")
backup_folder="bck_$(date +%Y%m%d_%H%M%S)"
for dir in "${directories[@]}"; do
  if [ -d "$dir" ]; then
    mkdir -p "$backup_folder"
    mv "$dir" "$backup_folder"
  fi
  mkdir "$dir"
done

# Generate raw data
echo ' '
echo '  ************************************ Generate raw data ************************************ '

echo ' procsim -s "Raw data generator: DATA-DUMP 1" procsim_config_raw.json'
wait_for_keypress
echo '  ************************************ Generate raw data for EO DATA-DUMP 1  --> '
procsim -s "Raw data generator: DATA-DUMP 1" procsim_config_raw.json

echo ' procsim -s "Raw data generator: DATA-DUMP 2" procsim_config_raw.json'
wait_for_keypress
echo '  ************************************ Generate raw data for EO DATA-DUMP 2  --> '
procsim -s "Raw data generator: DATA-DUMP 2" procsim_config_raw.json

echo ' procsim -s "Raw data generator: DATA-DUMP 3" procsim_config_raw.json'
wait_for_keypress
echo '  ************************************ Generate raw data for CAL DATA-DUMP  --> '
procsim -s "Raw data generator: DATA-DUMP 3" procsim_config_raw.json

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
echo ' L0 STEP 1: RAW HR1 DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR1_D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR1 DATA DUMP 1 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR1_D1.xml

echo ' L0 STEP 1: RAW HR2 DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR2_D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR2 DATA DUMP 1 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR2_D1.xml

echo ' L0 STEP 1: RAW LR DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-LR__D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW LR DATA DUMP 1 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-LR__D1.xml

echo ' L0 STEP 1: RAW HR1 DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR1_D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR1 DATA DUMP 2 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR1_D2.xml

echo ' L0 STEP 1: RAW HR2 DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-HR2_D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW HR2 DATA DUMP 2 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR2_D2.xml

echo ' L0 STEP 1: RAW LR DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-LR__D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW LR DATA DUMP 2 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-LR__D2.xml

echo ' L0 STEP 1: RAW OBC DATA DUMP 1 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-OBC_D1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW OBC DATA DUMP 1 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-OBC_D1.xml

echo ' L0 STEP 1: RAW OBC DATA DUMP 2 --> ./level0_step1.sh JobOrder.L0PF_S1_RAW-LR__D2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 1: RAW OBC DATA DUMP 2 --> '
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-OBC_D2.xml

echo ' '
echo ' '
echo ' '
echo '  ************************************ L0 STEP 2 ************************************ '
echo ' L0 STEP 2: HR2 Slice 3 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-HR2-Slice3.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: HR2 Slice 3 --> '
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR2-Slice3.xml

echo ' L0 STEP 2: HR1 Slice 7 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-HR1-Slice7.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: HR1 Slice 7  --> '
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR1-Slice7.xml

echo ' L0 STEP 2: HR2 VAU - orbit 1024 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-HR2-VAU-1024.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: HR2 VAU - orbit 1024  --> '
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR2-VAU-1024.xml

echo ' L0 STEP 2: LR VAU - orbit 1024 --> ./level0_step2.sh JobOrder.L0PF_S2_RWS-LR_-VAU-1024.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 2: LR VAU - orbit 1024  --> '
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-LR_-VAU-1024.xml

echo ' L0 STEP 2: Additional joborders'
wait_for_keypress
echo ' '
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR1-SliceCAL3.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR1-VAU-1025.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR1-VAU-1026.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR2-SliceCAL2.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR2-VAU-1025.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-HR2-VAU-1026.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-LR_-VAU-1025.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-LR_-VAU-1026.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-XS_ITM-1024.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-XS_ITM-1025.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-XS_ITM-1026.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-XS_OBC-1025.xml
./level0_step2.sh Scenario/JobOrder.L0PF_S2_RWS-XS_OBC-1026.xml

echo ' '
echo ' '
echo ' '
echo '  ************************************ L0 STEP 3 ************************************ '
echo ' L0 STEP 3: Slice 1 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-1.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 1 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-1.xml

echo ' L0 STEP 3: Slice 2 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-2.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 2 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-2.xml

echo ' L0 STEP 3: Slice 3 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-3.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 3 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-3.xml

echo ' L0 STEP 3: Slice 4 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-4.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 4 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-4.xml

echo ' L0 STEP 3: Slice 5 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-5.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 5 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-5.xml

echo ' L0 STEP 3: Slice 6 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-6.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 6 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-6.xml

echo ' L0 STEP 3: Slice 7 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-7.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 7 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-7.xml

echo ' L0 STEP 3: Slice 8 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-8.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 8 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-8.xml

echo ' L0 STEP 3: Slice 9 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-9.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 9 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-9.xml

echo ' L0 STEP 3: Slice 9 --> ./level0_step3.sh JobOrder.L0PF_S3_RWS-9.xml'
wait_for_keypress
echo ' '
echo '  ************************************ L0 STEP 3: Slice 9 --> '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-9.xml

# Added 2024/05/01
echo ' '
echo '  ************************************ L0 STEP 3: Additional steps --> '
echo ' '
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-CAL248.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-CAL249.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-CAL250.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-VAU-1024.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-VAU-1025.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-VAU-1026.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-XS_ITM-1024.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-XS_ITM-1025.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-XS_ITM-1026.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-XS_OBC-1024.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-XS_OBC-1025.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-XS_OBC-1026.xml

echo ' '
echo ' '
echo ' '
echo '  ************************************ L1 ************************************ '
wait_for_keypress
./level1.sh Scenario/JobOrder.L1PF_CAL_1.xml
./level1.sh Scenario/JobOrder.L1PF_CAL_2.xml
./level1.sh Scenario/JobOrder.L1PF_CAL_3.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_1.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_2.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_3.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_4.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_5.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_6.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_7.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_8.xml
./level1.sh Scenario/JobOrder.L1PF_OBS_9.xml

echo ' '
echo ' '
echo ' '
echo '  ************************************ L1C ************************************ '
echo ' L1C Slice 0 --> ./level1.sh JobOrder.L1CPF_OBS_1.xml'
wait_for_keypress
./level1.sh Scenario/JobOrder.L1CPF_OBS_1.xml

echo ' '
echo ' '
echo ' '
echo '  ******************************* L1C Floris only ***************************** '
echo ' L1C Slice 0 FLORIS only --> ./level1.sh JobOrder.L1CPF_FO_OBS_1.xml'
wait_for_keypress
./level1.sh Scenario/JobOrder.L1CPF_FO_OBS_1.xml

echo ' '
echo ' '
echo ' '
echo '  ******************************* L2  ************************************ '
echo ' L2 Slice 0 --> ./level2.sh JobOrder.L2_OBS_1.xml'
wait_for_keypress
./level2.sh Scenario/JobOrder.L2_OBS_1.xml
