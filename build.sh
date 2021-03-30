#!/bin/bash

# Copyright (C) 2021 S[&]T, The Netherlands.
# This script creates the procsim release package.

# retrieve version number
VERSION=`grep -Po "__version__[^']*'\K[^']*" procsim/core/version.py`

# create fresh package dir
PACKAGE=BIO_PROCSIM_RAW_L0_$VERSION
rm -rf $PACKAGE
mkdir $PACKAGE

# copy over release files
cp LICENSE $PACKAGE
cp README.md $PACKAGE
cp MANIFEST.in $PACKAGE
cp setup.py $PACKAGE
cp -R procsim $PACKAGE/procsim

# remove development stuff
cd $PACKAGE
rm -rf `find . -type d -name .git`
rm -rf `find . -type d -name __pycache__`
rm -rf `find . -type d -name test`
cd ..

# create tarball
tar zcf $PACKAGE.tgz $PACKAGE

# remove directory
rm -rf $PACKAGE

echo "Created package $PACKAGE"
