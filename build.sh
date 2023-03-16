#!/bin/bash

# Copyright (C) 2021 S[&]T, The Netherlands.
# This script creates the procsim release package.

# Exit when any command fails
set -e

# retrieve version number
VERSION=`grep -Po "__version__[^']*'\K[^']*" procsim/core/version.py`

# create fresh package dir
PACKAGE=PROCSIM_$VERSION
rm -rf $PACKAGE
mkdir $PACKAGE

# copy over release files
cp LICENSE $PACKAGE
cp README.md $PACKAGE
cp CHANGELOG $PACKAGE
cp MANIFEST.in $PACKAGE
cp setup.py $PACKAGE
cp Dockerfile $PACKAGE
cp -R procsim $PACKAGE/procsim
cp -R examples $PACKAGE/examples
cp -R examples_flex $PACKAGE/examples_flex

# remove development stuff
cd $PACKAGE
rm -rf `find . -type d -name .git`
rm -rf `find . -type d -name __pycache__`
rm -rf `find . -type d -name test`
rm -rf examples/data
rm -rf examples/workspace
cd ..

# create tarball
tar zcf $PACKAGE.tgz $PACKAGE

# remove directory
rm -rf $PACKAGE

echo "Created package $PACKAGE"
