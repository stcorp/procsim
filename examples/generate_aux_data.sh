#!/bin/sh
#-----------------------------------------------------------
# S&T procsim demo
#-----------------------------------------------------------

# Exit when any command fails
set -e

echo '  *** Generate aux data for Level 1 processor'
mkdir -p data
procsim -l debug -s "Aux generator" procsim_aux_scenario.json
