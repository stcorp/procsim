# Generate test data
mkdir -p data/AUX_CN0_AX
echo test > data/AUX_CN0_AX/AUX_CN0_AXVIEC20030723_000000_19910101_000000_20101231_235959
mkdir -p data/raw
python raw_generator.py data/raw

# Run test job
python pvml/pvml.py pvml/config.xml pvml/pvml_job_biomass_l0.xml
