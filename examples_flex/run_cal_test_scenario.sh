#!/bin/sh
set -x
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR1_D3.xml
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR1_D4.xml
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR2_D3.xml
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-HR2_D4.xml
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-LR__D3.xml
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-LR__D4.xml
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-OBC_D3.xml
./level0_step1.sh Scenario/JobOrder.L0PF_S1_RAW-OBC_D4.xml

./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-1.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-2.xml
./level0_step3.sh Scenario/JobOrder.L0PF_S3_RWS-3.xml
