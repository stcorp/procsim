'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw output product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0073

Biomass Level 0 output product generators,
format according to BIO-ESA-EOPG-EEGS-TN-0045
'''
import os

from biomass import product_name
from biomass import product_generator


class Sx_RAW__0x_generator(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Level-0 slice based products.
    '''

    PRODUCTS = ['S1_RAW__0S', 'S1_RAWP_0M', 'S1_RAW__0M',
                'S2_RAW__0S', 'S2_RAWP_0M', 'S2_RAW__0M',
                'S3_RAW__0S', 'S3_RAWP_0M', 'S3_RAW__0M',
                'RO_RAW__0S', 'RO_RAWP_0M',
                'EC_RAW__0S', 'EC_RAWP_0M']

    def __init__(self, logger, job_config, scenario_config: dict):
        super().__init__(logger, job_config, scenario_config)

    def generate_output(self):
        self.create_date, _ = self.hdr.get_phenomenon_times()   # HACK: fill in current date?

        name_gen = product_name.ProductName()
        name_gen.setup(self.output_type, self.start, self.stop, self.baseline_id, self.create_date)
        dir_name = name_gen.generate_path_name()

        self.hdr.set_product_type(self.output_type, self.baseline_id)
        self.hdr.set_product_filename(dir_name)
        self.hdr.set_validity_times(self.start, self.stop)

        # Create directory and files
        self.logger.info('Create {}'.format(dir_name))
        dir_name = os.path.join(self.output_path, dir_name)
        os.makedirs(dir_name, exist_ok=True)

        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        self.hdr.write(file_name)

        # H/V measurement data
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxh'))
        self._generate_bin_file(file_name, self.size//2)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_rxv'))
        self._generate_bin_file(file_name, self.size//2)

        # Ancillary products, low rate
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxh'))
        self._generate_bin_file(file_name)
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name('_ia_rxv'))
        self._generate_bin_file(file_name)
