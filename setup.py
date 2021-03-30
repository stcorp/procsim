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

setup(
    name="procsim",
    version=verstr,
    license="BSD3",
    author="S[&]T",
    description="Tool to simulate a processor in a PDGS.",
    # long_description="",
    packages=["procsim", "procsim.core", "procsim.biomass"],
    package_data={'procsim.core': ['*.xsd']},
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "procsim = procsim.core.main:main"
        ]
    },
)
