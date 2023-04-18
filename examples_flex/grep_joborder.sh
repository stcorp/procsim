#!/bin/sh
grep RAW_XS_LR__20170101T060131_20170101T060706 JobOrder.1.xml > /dev/null
exit_code=$?
if [ $exit_code -eq 0 ]; then
   echo "MATCH!"
fi
