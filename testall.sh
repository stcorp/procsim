#!/bin/sh
set -e

cd procsim
python3 -m unittest

cd ..
test/test.sh
