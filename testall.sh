#!/bin/sh
set -e

cd procsim
python -m unittest

cd ..
test/test.sh
