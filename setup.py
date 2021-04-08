import os
import re

from setuptools import setup

here = os.path.dirname(os.path.abspath(__file__))
VERSIONFILE = os.path.join(here, "procsim", "core", "version.py")
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in {}.".format(VERSIONFILE))

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name="procsim",
    version=verstr,
    url="https://www.stcorp.nl/",
    license="BSD3",
    author="S[&]T",
    author_email="info@stcorp.nl",
    description="Tool to simulate a processor in a PDGS.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=["procsim", "procsim.core", "procsim.biomass"],
    package_data={'procsim.core': ['*.xsd']},
    include_package_data=True,
    python_requires='>=3',
    entry_points={
        "console_scripts": [
            "procsim = procsim.core.main:main"
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Programming Language :: Python :: 3'
    ]
)
