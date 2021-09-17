'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass Mission Planning File (MPL) product generators,
format according to BIO-IC-ESC-FS-6005.
'''
import os
import zipfile
from typing import List

from . import constants, product_generator

_GENERATOR_PARAMS = [
    ('output_path', '_output_path', 'str'),
    ('file_class', '_file_class', 'str'),
    ('version_nr', '_version_nr', 'int'),
    ('zip_output', '_zip_output', 'bool'),
    ('zip_extension', '_zip_extension', 'str')
]
_HDR_PARAMS = [
    ('baseline', 'product_baseline', 'int'),
    ('begin_position', 'begin_position', 'date'),
    ('end_position', 'end_position', 'date'),
]
_ACQ_PARAMS = [
]


class Mpl(product_generator.ProductGeneratorBase):
    '''
    This class implements the ProductGeneratorBase and is responsible for
    generating Mission Planning File (MPL) products.

    By default, all MPL products consist of a single EOF file, which can be
    zipped.
    '''

    PRODUCTS = [
        'MPL_ORBREF', 'MPL_REFAUX', 'MPL_ORBPRE'
    ]
    DATETIME_FORMAT = '%Y%m%dT%H%M%S'

    @classmethod
    def time_to_str(cls, t):
        return t.strftime(cls.DATETIME_FORMAT)

    def __init__(self, logger, job_config, scenario_config: dict, output_config: dict):
        super().__init__(logger, job_config, scenario_config, output_config)
        self._file_class = 'OPER'
        self._version_nr = 1
        self._hdr.product_baseline = 0  # This is the default for MPL
        self._zip_output = False

    def get_params(self):
        gen, hdr, acq = super().get_params()
        return gen + _GENERATOR_PARAMS, hdr + _HDR_PARAMS, acq + _ACQ_PARAMS

    def _generate_file_name(self):
        return '{}_{}_{}_{}_{}_{:>02}{:>02}.EOF'.format(
            constants.SATELLITE_ID,
            self._file_class,
            self._output_type,
            self.time_to_str(self._hdr.begin_position),
            self.time_to_str(self._hdr.end_position),
            self._hdr.product_baseline,
            self._version_nr)

    def _zip_files(self, dir_name: str, filenames: List[str], arcnames: List[str]):
        # Note: Deletes input file(s) afterwards
        self._logger.debug('Archive to zip, extension {}'.format(self._zip_extension))
        with zipfile.ZipFile(dir_name + self._zip_extension, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for filename, arcname in zip(filenames, arcnames):
                zipped.write(filename, arcname)
                os.remove(filename)
            zipped.close()

    def generate_output(self):
        super().generate_output()

        file_name = self._generate_file_name()
        self._logger.info('Create {}'.format(file_name))
        os.makedirs(self._output_path, exist_ok=True)
        full_file_name = os.path.join(self._output_path, file_name)
        self._generate_bin_file(full_file_name, self._size_mb)

        if self._zip_output:
            base, extension = os.path.splitext(full_file_name)
            self._zip_files(base, [full_file_name], [file_name])
