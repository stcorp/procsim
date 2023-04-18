#!/bin/sh
if grep -q RAW_XS_LR__20170101T060131_20170101T060706 JobOrder.1.xml; then
   echo "MATCH!"
fi
