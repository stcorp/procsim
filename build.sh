#!/bin/bash

# Copyright (C) 2021 S[&]T, The Netherlands.
# This script creates the procsim release package.

# create fresh package dir
PACKAGE=${1:-procsim_package}
rm -rf $PACKAGE
mkdir $PACKAGE

# copy over release files
cp LICENSE $PACKAGE
cp README.md $PACKAGE
cp -R procsim $PACKAGE/procsim

# find .git, delete
cd $PACKAGE
rm -rf `find . -type d -name .git`
rm -rf `find . -type d -name __pycache__`
rm -rf `find . -type d -name test`
cd ..

# create tarball
tar zcf $PACKAGE.tgz $PACKAGE

# remove directory
rm -rf $PACKAGE
