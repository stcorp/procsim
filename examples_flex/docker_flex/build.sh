#!/bin/bash

# Copyright (C) 2023 S[&]T, The Netherlands.
#
# This script builds an image, based on the procism image,
# that also contains the flex configuration files.
#
# The image is tagged as procsim_flex and the config- and tasktable
# files can be found in /config and /tasktable respectively.

# Exit when any command fails
set -e

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# build the procism image
cd $DIR/../../
docker build -t procism .

# build the procism flex image
cd $DIR
docker build -f Dockerfile.flex_config -t procsim_flex .
