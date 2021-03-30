from setuptools import setup

setup(
    name="procsim",
    version="0.1.0",
    packages=["procsim", "procsim.core", "procsim.biomass"],
    entry_points={
        "console_scripts": [
            "procsim = procsim.core.main:main"
        ]
    },
)
