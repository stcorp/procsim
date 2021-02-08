#!/bin/sh
echo "-------------------------------------------------------"
echo "level0_task2.sh called!"
echo "Arguments: ${1} ${2} ${3} ${4} ${5}"

python3 ../../tasksim/tasksim.py $0 $1 ../../test/tasksim_config.json
