'''
Copyright (C) 2021 S[&]T, The Netherlands.

Parse and generate Biomass Main Product Headers.
Ref: BIO-ESA-EOPG-EEGS-TN-0051

TODO:
- Product URI
- Product size
- acquisitionType
- Product status
'''

import datetime
from logging import raiseExceptions
from typing import Optional
from xml.etree import ElementTree as et

import utils

from biomass import product_types

mph_namespaces = {
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
    'ows': "http://www.opengis.net/ows/2.0",
    'bio': "http://earth.esa.int/biomass/1.0",
    'sar': "http://www.opengis.net/sar/2.1",
    'xlink': "http://www.w3.org/1999/xlink",
    'om': "http://www.opengis.net/om/2.0",
    'gml': "http://www.opengis.net/gml/3.2",
    'eop': "http://www.opengis.net/eop/2.1",
}

# for ns, url in mph_namespaces.items():
#     locals()[ns] = "{%s}" % url
# Write in full, to avoid pylance warnings...
xsi = "{%s}" % mph_namespaces['xsi']
bio = "{%s}" % mph_namespaces['bio']
gml = "{%s}" % mph_namespaces['gml']
om = "{%s}" % mph_namespaces['om']
eop = "{%s}" % mph_namespaces['eop']
sar = "{%s}" % mph_namespaces['sar']
ows = "{%s}" % mph_namespaces['ows']
xlink = "{%s}" % mph_namespaces['xlink']


ISO_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
ISO_TIME_FORMAT_SHORT = '%Y-%m-%dT%H:%M:%S'


def _time_as_iso(tim: datetime.datetime) -> str:
    s = tim.strftime(ISO_TIME_FORMAT)
    return s[:-3] + 'Z'


def _time_from_iso(timestr: Optional[str]) -> Optional[datetime.datetime]:
    if timestr is None:
        return None
    timestr = timestr[:-1]  # strip 'Z'
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT)


def _time_as_iso_short(tim: datetime.datetime) -> str:
    return tim.strftime(ISO_TIME_FORMAT_SHORT) + 'Z'


def _time_from_iso_short(timestr: Optional[str]) -> Optional[datetime.datetime]:
    if timestr is None:
        return None
    timestr = timestr[:-1]  # strip 'Z'
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT_SHORT)


def _to_int(val: Optional[str]) -> Optional[int]:
    return int(val) if val is not None else None


def _to_bool(val: Optional[str]) -> Optional[bool]:
    return None if val is None else True if val == 'true' else False if val == 'false' else None


class Acquisition:
    '''
    Data class, hold acquisition parameters for MPH
    '''

    # These values are fixed for Biomass
    _polarisation_mode: str = 'Q'
    _polaristation_channels: str = 'HH, HV, VH, VV'
    _antenna_direction: str = 'LEFT'

    def __init__(self):
        # Fill with default values

        # L0, L1
        self.orbit_number: int = 0
        self.last_orbit_number: int = 0
        self.anx_date = datetime.datetime.now()
        self.start_time: int = 0           # in ms since ANX
        self.completion_time: int = 0      # in ms since ANX
        self.instrument_config_id: int = 0
        self.orbit_drift_flag: bool = False
        self.repeat_cycle_id: str = '__'    # 1..7 or DR or __, refer to PDGS Products Naming Convention document
        # RAWS, L0, L1, L2a
        self.slice_frame_nr: Optional[int] = None    # None or the actual slice/frame number
        # L0, L1, L2a
        self.orbit_direction: str = 'ASCENDING'      # Or DECENDING
        self.track_nr: int = 0                       # gml:CodeWithAuthorityType
        self.mission_phase: str = 'COMMISSIONING'    # Or INTERFEROMETRIC, TOMOGRAPHIC
        self.global_coverage_id: str = 'NA'          # 1..6 or NA, refer to PDGS Products Naming Convention document
        self.major_cycle_id: str = '1'               # 1..7, refer to PDGS Products Naming Convention document
        # AUT_ATT___, AUX_ORB___, L0, L1
        self.data_take_id: int = 0
        # self.feature_of_interest: str = ''

    def __eq__(self, other):
        return self.orbit_number == other.orbit_number and \
               self.last_orbit_number == other.last_orbit_number and \
               self.anx_date == other.anx_date and \
               self.start_time == other.start_time and \
               self.completion_time == other.completion_time and \
               self.instrument_config_id == other.instrument_config_id and \
               self.orbit_drift_flag == other.orbit_drift_flag and \
               self.major_cycle_id == other.major_cycle_id and \
               self.repeat_cycle_id == other.repeat_cycle_id and \
               self.slice_frame_nr == other.slice_frame_nr and \
               self.orbit_direction == other.orbit_direction and \
               self.track_nr == other.track_nr and \
               self.mission_phase == other.mission_phase and \
               self.global_coverage_id == other.global_coverage_id and \
               self.major_cycle_id == other.major_cycle_id and \
               self.data_take_id == other.data_take_id


class MainProductHeader:
    '''
    This class is responsible for parsing and creating the Biomass Main Product Header (MPH).
    '''

    # Fixed for Biomass
    _platform_shortname = 'Biomass'
    _sensor_name = 'P-SAR'
    _sensor_type = 'RADAR'
    _browse_type = 'QUICKLOOK'
    processing_mode = 'OPERATIONAL'

    def __init__(self):
        # These parameters MUST be set (no defaults)
        self.eop_identifier: Optional[str] = None
        self.begin_position: Optional[datetime.datetime] = None
        self.end_position: Optional[datetime.datetime] = None
        self.time_position: Optional[datetime.datetime] = None
        self.validity_start: Optional[datetime.datetime] = None
        self.validity_stop: Optional[datetime.datetime] = None
        self.product_baseline: Optional[int] = None
        self.processing_date: Optional[datetime.datetime] = None
        self.processor_name: Optional[str] = None
        self.processor_version: Optional[str] = None

        self._product_type: Optional[product_types.ProductType] = None
        self._processing_level = 'Other: L1'

        self.products = [
            {'file_name': 'product filename'},   # First product is mandatory and does not have the size/representation fields
            {'file_name': 'product filename', 'size': 100, 'representation': './schema/bio_l1_product.xsd'}
        ]
        self.doi = 'DOI'    # Digital Object Identifier
        self.acquisition_type = 'NOMINAL'   # OTHER, CALIBRATION or NOMINAL
        self.product_status = 'PLANNED'     # REJECTED, etc..
        self.processing_centre_code = 'ESR'
        self.auxiliary_ds_file_names = ['AUX_ORB_Filename', 'AUX_ATT_Filename']
        self.biomass_source_product_ids: list[str] = []
        self.reference_documents = []

        # Raw only
        self.acquisition_station: Optional[str] = None
        self.acquisition_date: Optional[datetime.datetime] = None
        # Raw, HKTM only
        self.nr_transfer_frames = None
        self.nr_transfer_frames_erroneous = None
        self.nr_transfer_frames_corrupt = None
        # Raw, science/ancillary only
        self.nr_instrument_source_packets = None
        self.nr_instrument_source_packets_erroneous = None
        self.nr_instrument_source_packets_corrupt = None

        # L0 only
        self.nr_l0_lines: Optional[str] = None           # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.nr_l0_lines_missing: Optional[str] = None   # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.nr_l0_lines_corrupt: Optional[str] = None   # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.incomplete_l0_slice: Optional[bool] = None
        self.partial_l0_slice: Optional[bool] = None
        self.l1_frames_in_l0: Optional[str] = None      # '0,1,2,4,5'

        # L1 only
        self.incomplete_l1_frame: Optional[bool] = None
        self.partial_l1_frame: Optional[bool] = None
        self.browse_ref_id: Optional[str] = None
        self.browse_image_filename: Optional[str] = None

        # L0 and L1
        acquisition = Acquisition()
        self.acquisitions = [acquisition]
        self.tai_utc_diff = 0

        # L0, L1, L2a
        self.sensor_swath = None    # Mode is SM, RO, EC, AC, swath is S1, S2, S3
        self.sensor_mode = None

        # L1, L2a
        self.footprint_polygon: Optional[str] = None
        self.center_points: Optional[str] = None

        for key, value in mph_namespaces.items():
            et.register_namespace(key, value)

    def __eq__(self, other):
        return \
            self.eop_identifier == other.eop_identifier and \
            self.begin_position == other.begin_position and \
            self.end_position == other.end_position and \
            self.time_position == other.time_position and \
            self.validity_start == other.validity_start and \
            self.validity_stop == other.validity_stop and \
            self._product_type == other._product_type and \
            self.product_baseline == other.product_baseline and \
            self.processing_date == other.processing_date and \
            self.processor_name == other.processor_name and \
            self.processor_version == other.processor_version and \
            self.acquisitions == other.acquisitions and \
            self.doi == other.doi and \
            self.acquisition_type == other.acquisition_type and \
            self.product_status == other.product_status and \
            self.processing_centre_code == other.processing_centre_code and \
            self._processing_level == other._processing_level and \
            self.auxiliary_ds_file_names == other.auxiliary_ds_file_names and \
            self.biomass_source_product_ids == other.biomass_source_product_ids and \
            self.reference_documents == other.reference_documents and \
            self.acquisition_station == other.acquisition_station and \
            self.acquisition_date == other.acquisition_date and \
            self.nr_transfer_frames == other.nr_transfer_frames and \
            self.nr_transfer_frames_erroneous == other.nr_transfer_frames_erroneous and \
            self.nr_transfer_frames_corrupt == other.nr_transfer_frames_corrupt and \
            self.nr_instrument_source_packets == other.nr_instrument_source_packets and \
            self.nr_instrument_source_packets_erroneous == other.nr_instrument_source_packets_erroneous and \
            self.nr_instrument_source_packets_corrupt == other.nr_instrument_source_packets_corrupt and \
            self.nr_l0_lines == other.nr_l0_lines and \
            self.nr_l0_lines_missing == other.nr_l0_lines_missing and \
            self.nr_l0_lines_corrupt == other.nr_l0_lines_corrupt and \
            self.incomplete_l0_slice == other.incomplete_l0_slice and \
            self.partial_l0_slice == other.partial_l0_slice and \
            self.l1_frames_in_l0 == other.l1_frames_in_l0 and \
            self.incomplete_l1_frame == other.incomplete_l1_frame and \
            self.partial_l1_frame == other.partial_l1_frame and \
            self.browse_ref_id == other.browse_ref_id and \
            self.browse_image_filename == other.browse_image_filename and \
            self.tai_utc_diff == other.tai_utc_diff and \
            self.sensor_swath == other.sensor_swath and \
            self.sensor_mode == other.sensor_mode and \
            self.footprint_polygon == other.footprint_polygon and \
            self.center_points == other.center_points

    @property
    def product_type(self):
        return self._product_type.type

    @product_type.setter
    def product_type(self, type: str):
        '''
        Type must be one of the predefined BIOMASS types
        '''
        product_type = product_types.find_product(type)
        if product_type is not None:
            self._product_type = product_type
            self._processing_level = 'other: {}'.format(product_type.level.upper())
        else:
            raise Exception('Unknown product type {}'.format(type))

    def set_product_filename(self, filename: str):
        '''
        Must be the directory name (without path)
        '''
        self.eop_identifier = filename
        self.products[0] = {'file_name': filename}

    def set_phenomenon_times(self, start, end):
        '''
        Start/stop are UTC start date and time:
            - Acquisition sensing time for RAW, L0
            - Acquisition Zero Doppler Time for L1
            - Validity start time for AUX
            - Acquisition Zero Doppler Time, start of first image in the Stack for L2A
        '''
        self.begin_position = start
        self.end_position = end
        self.time_position = end  # = end, according to MPH definition

    def set_validity_times(self, start, stop):
        '''
        Start/stop are UTC start date and time:
            - Acquisition sensing time for RAW_<PID>_<PC>, RAW___HKTM
            - Slice start time for RAWS<PID>_<PC>, L0
            - Frame start time for L1
            - Validity start time for AUX
            - Frame start time of first image in the Stack for *L2A
        '''
        self.validity_start = start
        self.validity_stop = stop

    def set_processing_parameters(self, name: str, version: str, date: datetime.datetime):
        self.processor_name = name
        self.processor_version = version
        self.processing_date = date

    def _insert_time_period(self, parent, start: datetime.datetime, stop: datetime.datetime, id):
        # Insert TimePeriod element
        time_period = et.SubElement(parent, gml + 'TimePeriod')
        time_period.set(gml + 'id', self.eop_identifier + '_' + str(id))
        begin_position = et.SubElement(time_period, gml + 'beginPosition')
        begin_position.text = _time_as_iso(start)    # Start date and time of the product
        end_position = et.SubElement(time_period, gml + 'endPosition')
        end_position.text = _time_as_iso(stop)       # Stop date and time of the product

    def _parse_time_period(self, parent, id):
        # Parse TimePeriod element, retrieve start/stop
        time_period = parent.find(gml + 'TimePeriod')
        begin_position = time_period.find(gml + 'beginPosition')
        begin = _time_from_iso(begin_position.text)
        end_position = time_period.find(gml + 'endPosition')
        end = _time_from_iso(end_position.text)
        return begin, end

    def _insert_file_name(self, parent, file_name):
        # Insert fileName element
        file_name_el = et.SubElement(parent, eop + 'fileName')
        service_reference = et.SubElement(file_name_el, ows + 'ServiceReference')
        service_reference.set(xlink + 'href', file_name)
        et.SubElement(service_reference, ows + 'RequestMessage')  # download request (empty)

    def _parse_file_name(self, parent):
        # Parse fileName element
        file_name_el = parent.find(eop + 'fileName')
        service_reference = file_name_el.find(ows + 'ServiceReference')
        file_name = service_reference.get(xlink + 'href')
        # et.SubElement(service_reference, ows + 'RequestMessage')  # download request (empty)
        return file_name

    def write(self, file_name):
        # Create MPH and write to file (TODO: split in generate and write methods?)
        level = self._product_type.level

        mph = et.Element(bio + 'EarthObservation')
        mph.set(gml + 'id', self.eop_identifier + '_1')

        # Some parameters have no default and MUST be set prior to generation
        if self.begin_position is None or self.end_position is None or \
                self.validity_start is None or self.validity_stop is None or \
                self.time_position is None:
            raise Exception('Times must be set before creating MPH')

        phenomenon_time = et.SubElement(mph, om + 'phenomenonTime')
        self._insert_time_period(phenomenon_time, self.begin_position, self.end_position, 2)

        result_time = et.SubElement(mph, om + 'resultTime')
        time_instant = et.SubElement(result_time, gml + 'TimeInstant')
        time_instant.set(gml + 'id', self.eop_identifier + '_3')
        time_position = et.SubElement(time_instant, gml + 'timePosition')
        time_position.text = _time_as_iso(self.time_position)

        valid_time = et.SubElement(mph, om + 'validTime')
        self._insert_time_period(valid_time, self.validity_start, self.validity_stop, 4)

        procedure = et.SubElement(mph, om + 'procedure')  # Procedure used to sense the data
        earth_observation_equipment = et.SubElement(procedure, eop + 'EarthObservationEquipment')  # Equipment used to sense the data
        earth_observation_equipment.set(gml + 'id', self.eop_identifier + '_5')
        platform = et.SubElement(earth_observation_equipment, eop + 'platform')  # Platform description
        Platform = et.SubElement(platform, eop + 'Platform')  # Nested element for platform description
        short_name = et.SubElement(Platform, eop + 'shortName')
        short_name.text = self._platform_shortname

        instrument = et.SubElement(earth_observation_equipment, eop + 'instrument')  # Instrument description
        Instrument = et.SubElement(instrument, eop + 'Instrument')  # Nested element for instrument description
        short_name = et.SubElement(Instrument, eop + 'shortName')
        short_name.text = self._sensor_name

        # Mandatory for L0, L1, L2A products
        sensors = [{'type': self._sensor_type, 'mode': self.sensor_mode, 'swath_id': self.sensor_swath}]
        if (level == 'l0' or level == 'l1' or level == 'l2a'):
            sensor = et.SubElement(earth_observation_equipment, eop + 'sensor')  # Sensor description
            Sensor = et.SubElement(sensor, eop + 'Sensor')  # Nested element for sensor description
            for s in sensors:
                sensor_type = et.SubElement(Sensor, eop + 'sensorType')
                sensor_type.text = s['type']
                sensor_mode = et.SubElement(Sensor, eop + 'operationalMode')
                sensor_mode.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:operationalMode')
                sensor_mode.text = s['mode']
                swath_id = et.SubElement(Sensor, eop + 'swathIdentifier')
                swath_id.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:swathIdentifier')
                swath_id.text = s['swath_id']

        if level in ['l0', 'l1', 'l2a'] or self._product_type in ['AUX_ATT___', 'AUX_ORB___']:
            acquisition_params = et.SubElement(earth_observation_equipment, eop + 'acquisitionParameters')
            acquisition = et.SubElement(acquisition_params, bio + 'Acquisition')
            for acq in self.acquisitions:
                if level in ['l0', 'l1']:
                    et.SubElement(acquisition, eop + 'orbitNumber').text = str(acq.orbit_number)  # orbit start
                    et.SubElement(acquisition, eop + 'lastOrbitNumber').text = str(acq.last_orbit_number)   # orbit stop
                if level in ['l0', 'l1', 'l2a']:
                    et.SubElement(acquisition, eop + 'orbitDirection').text = acq.orbit_direction
                    tracknr = et.SubElement(acquisition, eop + 'wrsLongitudeGrid')
                    tracknr.text = str(acq.track_nr)
                    tracknr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:relativeOrbits')
                if level in ['l0', 'l1', 'l2a'] or self._product_type.type in product_types.RAWS_PRODUCT_TYPES:
                    framenr = et.SubElement(acquisition, eop + 'wrsLatitudeGrid')
                    framenr.text = str(acq.slice_frame_nr) if acq.slice_frame_nr is not None else '___'
                    framenr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:frames')
                if level in ['l0', 'l1']:
                    et.SubElement(acquisition, eop + 'ascendingNodeDate').text = _time_as_iso(acq.anx_date)
                    et.SubElement(acquisition, eop + 'startTimeFromAscendingNode', attrib={'uom': 'ms'}).text = str(acq.start_time)
                    et.SubElement(acquisition, eop + 'completionTimeFromAscendingNode', attrib={'uom': 'ms'}).text = str(acq.completion_time)
                    et.SubElement(acquisition, sar + 'polarisationMode').text = acq._polarisation_mode
                    et.SubElement(acquisition, sar + 'polarisationChannels').text = acq._polaristation_channels
                if level in ['l0', 'l1', 'l2a']:
                    et.SubElement(acquisition, sar + 'antennaLookDirection').text = acq._antenna_direction
                    et.SubElement(acquisition, bio + 'missionPhase').text = acq.mission_phase
                if level in ['l0', 'l1']:
                    et.SubElement(acquisition, bio + 'instrumentConfID').text = str(acq.instrument_config_id)
                if level in ['l0', 'l1'] or self._product_type in ['AUX_ATT___', 'AUX_ORB___']:
                    et.SubElement(acquisition, bio + 'dataTakeID').text = str(acq.data_take_id)
                if level in ['l0', 'l1']:
                    et.SubElement(acquisition, bio + 'orbitDriftFlag').text = str(acq.orbit_drift_flag).lower()
                if level in ['l0', 'l1', 'l2a']:
                    et.SubElement(acquisition, bio + 'globalCoverageID').text = acq.global_coverage_id
                    et.SubElement(acquisition, bio + 'majorCycleID').text = acq.major_cycle_id
                if level in ['l0', 'l1']:
                    et.SubElement(acquisition, bio + 'repeatCycleID').text = acq.repeat_cycle_id

        observed_property = et.SubElement(mph, om + 'observedProperty')  # Observed property (Mandatory but empty)
        observed_property.set(xsi + 'nil', 'true')
        observed_property.set('nilReason', 'inapplicable')
        feature_of_interest = et.SubElement(mph, om + 'featureOfInterest')  # Observed area

        if level in ['l1', 'l2a']:
            footprint = et.SubElement(feature_of_interest, eop + 'Footprint')
            footprint.set(gml + 'id', self.eop_identifier + '_6')
            multi_extent_of = et.SubElement(footprint, eop + 'multiExtentOf')  # Footprint representation structure, coordinates in posList
            multi_surface = et.SubElement(multi_extent_of, gml + 'MultiSurface')
            multi_surface.set(gml + 'id', self.eop_identifier + '_7')
            surface_member = et.SubElement(multi_surface, gml + 'surfaceMember')
            polygon = et.SubElement(surface_member, gml + 'Polygon')
            polygon.set(gml + 'id', self.eop_identifier + '_8')
            exterior = et.SubElement(polygon, gml + 'exterior')
            linear_ring = et.SubElement(exterior, gml + 'LinearRing')
            pos_list = et.SubElement(linear_ring, gml + 'posList')  # Footprint points
            pos_list.text = self.footprint_polygon

            #
            # TODO! This is a discrepancy between spec and example!!
            #
            # center_of = et.SubElement(feature_of_interest, eop + 'centerOf')  # Acquisition centre representation structure
            center_of = et.SubElement(footprint, eop + 'centerOf')  # Acquisition centre representation structure

            point = et.SubElement(center_of, gml + 'Point')
            point.set(gml + 'id', self.eop_identifier + '_9')
            pos = et.SubElement(point, gml + 'pos')  # Coordinates of the centre of the acquisition
            pos.text = self.center_points

        result = et.SubElement(mph, om + 'result')  # Observation result
        earth_observation_result = et.SubElement(result, eop + 'EarthObservationResult')
        earth_observation_result.set(gml + 'id', self.eop_identifier + '_10')

        if level in ['l1']:
            browse = et.SubElement(earth_observation_result, eop + 'browse')
            browse_info = et.SubElement(browse, eop + 'BrowseInformation')
            browse_type = et.SubElement(browse_info, eop + 'type').text = self._browse_type
            browse_ref_id = et.SubElement(browse_info, eop + 'referenceSystemIdentifier')  # Coordinate reference system name
            browse_ref_id.set('codeSpace', 'urn:esa:eop:crs')
            browse_ref_id.text = self.browse_ref_id
            self._insert_file_name(browse_info, self.browse_image_filename)

        for prod in self.products:
            product = et.SubElement(earth_observation_result, eop + 'product')
            product_information = et.SubElement(product, bio + 'ProductInformation')
            self._insert_file_name(product_information, prod['file_name'])
            if 'size' in prod:
                et.SubElement(product_information, eop + 'size', attrib={'uom': 'bytes'}).text = str(prod['size'])
                if prod['representation'] is not None:    # Mandatory for if type is XML
                    et.SubElement(product_information, bio + 'rds').text = prod['representation']
            else:
                et.SubElement(product_information, eop + 'version').text = '{:02}'.format(self.product_baseline)

        meta_data_property = et.SubElement(mph, eop + 'metaDataProperty')  # Observation metadata
        earth_observation_meta_data = et.SubElement(meta_data_property, bio + 'EarthObservationMetaData')
        et.SubElement(earth_observation_meta_data, eop + 'identifier').text = self.eop_identifier
        et.SubElement(earth_observation_meta_data, eop + 'doi').text = self.doi  # Digital Object Identifier'
        et.SubElement(earth_observation_meta_data, eop + 'acquisitionType').text = self.acquisition_type
        # TODO: Write product type here? Ref says: "Describes product type in case that mixed types
        # are available within a single collection, this is ground segment specific definition"
        et.SubElement(earth_observation_meta_data, eop + 'productType').text = self._product_type.type
        et.SubElement(earth_observation_meta_data, eop + 'status').text = self.product_status

        if level in ['raw']:
            if self.acquisition_date is None or self.acquisition_station is None:
                raise Exception('Acquisition time/station must be set prior to generating MPH')
            downlinked_to = et.SubElement(earth_observation_meta_data, eop + 'downlinkedTo')
            downlink_info = et.SubElement(downlinked_to, eop + 'DownlinkInformation')
            et.SubElement(downlink_info, eop + 'acquisitionStation').text = self.acquisition_station
            et.SubElement(downlink_info, eop + 'acquisitionDate').text = _time_as_iso(self.acquisition_date)

        processing = et.SubElement(earth_observation_meta_data, eop + 'processing')  # Data processing information
        processing_info = et.SubElement(processing, bio + 'ProcessingInformation')
        proc_center = et.SubElement(processing_info, eop + 'processingCenter')
        proc_center.text = self.processing_centre_code
        proc_center.set('codeSpace', 'urn:esa:eop:Biomass:facility')
        if self.processing_date is None or self.processor_name is None or \
                self.processor_version is None or self._processing_level is None:
            raise Exception('Processing parameters must be set prior to generating MPH')
        et.SubElement(processing_info, eop + 'processingDate').text = _time_as_iso_short(self.processing_date)
        et.SubElement(processing_info, eop + 'processorName').text = self.processor_name
        et.SubElement(processing_info, eop + 'processorVersion').text = self.processor_version
        et.SubElement(processing_info, eop + 'processingLevel').text = self._processing_level

        if level not in ['aux']:
            for name in self.auxiliary_ds_file_names:
                et.SubElement(processing_info, eop + 'auxiliaryDataSetFileName').text = name

        et.SubElement(processing_info, eop + 'processingMode', attrib={'codespace': 'urn:esa:eop:Biomass:class'}).text = self.processing_mode

        if level in ['l0', 'l1', 'l2a']:
            for id in self.biomass_source_product_ids:
                et.SubElement(processing_info, bio + 'sourceProduct').text = id

        if level in ['l0', 'l1']:
            et.SubElement(earth_observation_meta_data, bio + 'TAI-UTC').text = str(self.tai_utc_diff)

        if level in ['raw']:
            if self._product_type.type == 'RAW___HKTM':
                et.SubElement(earth_observation_meta_data, bio + 'numOfTFs').text = str(self.nr_transfer_frames)
                et.SubElement(earth_observation_meta_data, bio + 'numOfTFsWithErrors').text = str(self.nr_transfer_frames_erroneous)
                et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedTFs').text = str(self.nr_transfer_frames_corrupt)
            else:
                et.SubElement(earth_observation_meta_data, bio + 'numOfISPs').text = str(self.nr_instrument_source_packets)
                et.SubElement(earth_observation_meta_data, bio + 'numOfISPsWithErrors').text = str(self.nr_instrument_source_packets_erroneous)
                et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedISPs').text = str(self.nr_instrument_source_packets_corrupt)

        if level in ['l0']:
            et.SubElement(earth_observation_meta_data, bio + 'numOfLines').text = self.nr_l0_lines
            et.SubElement(earth_observation_meta_data, bio + 'numOfMissingLines').text = self.nr_l0_lines_missing
            et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedLines').text = self.nr_l0_lines_corrupt
            et.SubElement(earth_observation_meta_data, bio + 'incompleteSlice').text = str(self.incomplete_l0_slice).lower()
            et.SubElement(earth_observation_meta_data, bio + 'partialSlice').text = str(self.partial_l0_slice).lower()
            et.SubElement(earth_observation_meta_data, bio + 'framesList').text = self.l1_frames_in_l0

        if level in ['l1']:
            et.SubElement(earth_observation_meta_data, bio + 'incompleteFrame').text = str(self.incomplete_l1_frame).lower()
            et.SubElement(earth_observation_meta_data, bio + 'partialFrame').text = str(self.partial_l1_frame).lower()

        for doc in self.reference_documents:
            et.SubElement(earth_observation_meta_data, bio + 'refDoc').text = doc

        # Create XML
        tree = et.ElementTree(mph)
        utils.indent_xml(tree.getroot())
        tree.write(file_name, xml_declaration=True, encoding='utf-8')

    def parse(self, file_name):
        '''Open MPH file and parse contents. Does not check for ID's.'''
        tree = et.parse(file_name)
        root = tree.getroot()
        phenomenon_time = root.find(om + 'phenomenonTime')
        self.begin_position, self.end_position = self._parse_time_period(phenomenon_time, 2)

        result_time = root.find(om + 'resultTime')
        time_instant = result_time.find(gml + 'TimeInstant')
        # time_instant.set(gml + 'id', self.eop_identifier + '_3')
        self.time_position = _time_from_iso(time_instant.findtext(gml + 'timePosition'))

        valid_time = root.find(om + 'validTime')
        self.validity_start, self.validity_stop = self._parse_time_period(valid_time, 4)

        procedure = root.find(om + 'procedure')  # Procedure used to sense the data
        earth_observation_equipment = procedure.find(eop + 'EarthObservationEquipment')  # Equipment used to sense the data
        # earth_observation_equipment.set(gml + 'id', self.eop_identifier + '_5')
        platform = earth_observation_equipment.find(eop + 'platform')  # Platform description
        Platform = platform.find(eop + 'Platform')  # Nested element for platform description
        self._platform_shortname = Platform.findtext(eop + 'shortName')

        instrument = earth_observation_equipment.find(eop + 'instrument')  # Instrument description
        Instrument = instrument.find(eop + 'Instrument')  # Nested element for instrument description
        self._sensor_name = Instrument.findtext(eop + 'shortName')

        # Mandatory for L0, L1, L2A products
        sensors = []
        # TODO: check if the 'sensor' element is mandatory, even if there are no sensors.
        sensor = earth_observation_equipment.find(eop + 'sensor')
        if sensor is not None:
            for Sensor in sensor.findall(eop + 'Sensor'):
                s = {}
                s['type'] = Sensor.findtext(eop + 'sensorType')
                s['mode'] = Sensor.findtext(eop + 'operationalMode')
                # sensor_mode.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:operationalMode')
                s['swath_id'] = Sensor.findtext(eop + 'swathIdentifier')
                # swath_id.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:swathIdentifier')
                sensors.append(s)

        # Assume there are 0 or 1 sensors
        if sensors:
            self.sensor_swath = sensors[0]['swath_id']
            self.sensor_mode = sensors[0]['mode']

        acquisition_params = earth_observation_equipment.find(eop + 'acquisitionParameters')
        if acquisition_params is not None:
            # TODO: Clear the list. Drawback: existing values are gone now. Other option is to
            # overwrite the existing values and append new acquisitions if there are more.
            self.acquisitions.clear()
            for acquisition in acquisition_params.findall(bio + 'Acquisition'):
                acq = Acquisition()
                acq.orbit_number = _to_int(acquisition.findtext(eop + 'orbitNumber')) or acq.orbit_number
                acq.last_orbit_number = _to_int(acquisition.findtext(eop + 'lastOrbitNumber')) or acq.last_orbit_number
                acq.orbit_direction = acquisition.findtext(eop + 'orbitDirection') or acq.orbit_direction
                acq.track_nr = _to_int(acquisition.findtext(eop + 'wrsLongitudeGrid')) or acq.track_nr
                # tracknr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:relativeOrbits')
                nr = acquisition.findtext(eop + 'wrsLatitudeGrid')
                if nr is not None:
                    acq.slice_frame_nr = int(nr) if not nr == '___' else None
                # framenr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:frames')
                acq.anx_date = _time_from_iso(acquisition.findtext(eop + 'ascendingNodeDate')) or acq.anx_date
                # TODO ={'uom': 'ms'}
                acq.start_time = _to_int(acquisition.findtext(eop + 'startTimeFromAscendingNode')) or acq.start_time
                # TODO ={'uom': 'ms'}
                acq.completion_time = _to_int(acquisition.findtext(eop + 'completionTimeFromAscendingNode')) or acq.completion_time

                # TODO: Only CHECK these, not overwrite!
                acq._polarisation_mode = acquisition.findtext(sar + 'polarisationMode') or acq._polarisation_mode
                acq._polaristation_channels = acquisition.findtext(sar + 'polarisationChannels') or acq._polaristation_channels
                acq._antenna_direction = acquisition.findtext(sar + 'antennaLookDirection') or acq._antenna_direction

                acq.mission_phase = acquisition.findtext(bio + 'missionPhase') or acq.mission_phase
                acq.instrument_config_id = _to_int(acquisition.findtext(bio + 'instrumentConfID')) or acq.instrument_config_id
                acq.data_take_id = _to_int(acquisition.findtext(bio + 'dataTakeID')) or acq.data_take_id
                orbit_drift_flag = acquisition.findtext(bio + 'orbitDriftFlag')
                if orbit_drift_flag is not None:
                    acq.orbit_drift_flag = orbit_drift_flag.lower() == 'true'
                acq.global_coverage_id = acquisition.findtext(bio + 'globalCoverageID') or acq.global_coverage_id
                acq.major_cycle_id = acquisition.findtext(bio + 'majorCycleID') or acq.major_cycle_id
                acq.repeat_cycle_id = acquisition.findtext(bio + 'repeatCycleID') or acq.repeat_cycle_id
                self.acquisitions.append(acq)

        # observed_property = root.find(om + 'observedProperty')  # Observed property (Mandatory but empty)
        # observed_property.set(xsi + 'nil', 'true')
        # observed_property.set('nilReason', 'inapplicable')
        feature_of_interest = root.find(om + 'featureOfInterest')  # Observed area

        # Mandatory for L1, *L2A products
        footprint = feature_of_interest.find(eop + 'Footprint')
        if footprint is not None:
            # footprint.set(gml + 'id', self.eop_identifier + '_6')
            multi_extent_of = footprint.find(eop + 'multiExtentOf')  # Footprint representation structure, coordinates in posList
            multi_surface = multi_extent_of.find(gml + 'MultiSurface')
            # multi_surface.set(gml + 'id', self.eop_identifier + '_7')
            surface_member = multi_surface.find(gml + 'surfaceMember')
            polygon = surface_member.find(gml + 'Polygon')
            # polygon.set(gml + 'id', self.eop_identifier + '_8')
            exterior = polygon.find(gml + 'exterior')
            linear_ring = exterior.find(gml + 'LinearRing')
            self.footprint_polygon = linear_ring.findtext(gml + 'posList')  # Footprint points

            #
            # TODO! This is a discrepancy between spec and example!!
            #

            # center_of = feature_of_interest.find(eop + 'centerOf')  # Acquisition centre representation structure
            center_of = footprint.find(eop + 'centerOf')  # Acquisition centre representation structure

            point = center_of.find(gml + 'Point')
            # point.set(gml + 'id', self.eop_identifier + '_9')
            self.center_points = point.findtext(gml + 'pos')  # Coordinates of the centre of the acquisition

        result = root.find(om + 'result')  # Observation result
        earth_observation_result = result.find(eop + 'EarthObservationResult')
        # earth_observation_result.set(gml + 'id', self.eop_identifier + '_10')

        # Mandatory for L1 products
        browse = earth_observation_result.find(eop + 'browse')
        if browse is not None:
            browse_info = browse.find(eop + 'BrowseInformation')
            self._browse_type = browse_info.findtext(eop + 'type')
            self.browse_ref_id = browse_info.findtext(eop + 'referenceSystemIdentifier')  # Coordinate reference system name
            # browse_ref_id.set('codeSpace', 'urn:esa:eop:crs')
            # self._insert_file_name(browse_info, self.browse_image_filename)
            self.browse_image_filename = self._parse_file_name(browse_info)

        self.products.clear()
        for product in earth_observation_result.findall(eop + 'product'):
            product_information = product.find(bio + 'ProductInformation')
            file_name = self._parse_file_name(product_information)
            version = product_information.findtext(eop + 'version')
            if version is not None:
                self.product_baseline = int(version)
                self.products.append({'file_name': file_name})
            else:
                size = int(product_information.findtext(eop + 'size', '0'))  # attrib={'uom': 'bytes'}
                representation = product_information.findtext(bio + 'rds')
                self.products.append({'file_name': file_name, 'size': size, 'representation': representation})

        meta_data_property = root.find(eop + 'metaDataProperty')  # Observation metadata
        earth_observation_meta_data = meta_data_property.find(bio + 'EarthObservationMetaData')
        self.eop_identifier = earth_observation_meta_data.findtext(eop + 'identifier')
        self.doi = earth_observation_meta_data.find(eop + 'doi').text  # Digital Object Identifier'
        self.acquisition_type = earth_observation_meta_data.findtext(eop + 'acquisitionType')
        type_code = earth_observation_meta_data.findtext(eop + 'productType', '')
        type = product_types.find_product(type_code)
        if type is not None:
            self._product_type = type
        self.product_status = earth_observation_meta_data.findtext(eop + 'status')

        # Mandatory for Raw data: Downlink information
        downlinked_to = earth_observation_meta_data.find(eop + 'downlinkedTo')
        if downlinked_to is not None:
            downlink_info = downlinked_to.find(eop + 'DownlinkInformation')
            self.acquisition_station = downlink_info.findtext(eop + 'acquisitionStation')
            self.acquisition_date = _time_from_iso(downlink_info.findtext(eop + 'acquisitionDate'))

        processing = earth_observation_meta_data.find(eop + 'processing')  # Data processing information
        processing_info = processing.find(bio + 'ProcessingInformation')
        self.processing_centre_code = processing_info.findtext(eop + 'processingCenter')
        # proc_center.set('codeSpace', 'urn:esa:eop:Biomass:facility')
        self.processing_date = _time_from_iso_short(processing_info.findtext(eop + 'processingDate'))
        self.processor_name = processing_info.findtext(eop + 'processorName')
        self.processor_version = processing_info.findtext(eop + 'processorVersion')
        self._processing_level = processing_info.findtext(eop + 'processingLevel')

        self.auxiliary_ds_file_names.clear()
        for proc_info in processing_info.findall(eop + 'auxiliaryDataSetFileName'):
            if proc_info.text is not None:
                self.auxiliary_ds_file_names.append(proc_info.text)

        self.processing_mode = processing_info.find(eop + 'processingMode').text    # attrib={'codespace': 'urn:esa:eop:Biomass:class'}

        # Mandatory for level 0, 1 and 2a
        self.biomass_source_product_ids.clear()
        for source_product in processing_info.findall(bio + 'sourceProduct'):
            if source_product.text is not None:
                self.biomass_source_product_ids.append(source_product.text)

        # Mandatory for level 0 and 1
        tai_utc = earth_observation_meta_data.findtext(bio + 'TAI-UTC')
        if tai_utc is not None:
            self.tai_utc_diff = int(tai_utc)

        # Manadatory for raw
        self.nr_transfer_frames = _to_int(earth_observation_meta_data.findtext(bio + 'numOfTFs'))
        self.nr_transfer_frames_erroneous = _to_int(earth_observation_meta_data.findtext(bio + 'numOfTFsWithErrors'))
        self.nr_transfer_frames_corrupt = _to_int(earth_observation_meta_data.findtext(bio + 'numOfCorruptedTFs'))

        self.nr_instrument_source_packets = _to_int(earth_observation_meta_data.findtext(bio + 'numOfISPs'))
        self.nr_instrument_source_packets_erroneous = _to_int(earth_observation_meta_data.findtext(bio + 'numOfISPsWithErrors'))
        self.nr_instrument_source_packets_corrupt = _to_int(earth_observation_meta_data.findtext(bio + 'numOfCorruptedISPs'))

        # Mandatory for level 0. Note: these are all pairs of numbers
        self.nr_l0_lines = earth_observation_meta_data.findtext(bio + 'numOfLines')
        self.nr_l0_lines_missing = earth_observation_meta_data.findtext(bio + 'numOfMissingLines')
        self.nr_l0_lines_corrupt = earth_observation_meta_data.findtext(bio + 'numOfCorruptedLines')
        self.incomplete_l0_slice = _to_bool(earth_observation_meta_data.findtext(bio + 'incompleteSlice'))
        self.partial_l0_slice = _to_bool(earth_observation_meta_data.findtext(bio + 'partialSlice'))
        self.l1_frames_in_l0 = earth_observation_meta_data.findtext(bio + 'framesList')

        # Level 1
        self.incomplete_l1_frame = _to_bool(earth_observation_meta_data.findtext(bio + 'incompleteFrame'))
        self.partial_l1_frame = _to_bool(earth_observation_meta_data.findtext(bio + 'partialFrame'))

        self.reference_documents.clear()
        for doc in earth_observation_meta_data.findall(bio + 'refDoc'):
            if doc.text is not None:
                self.reference_documents.append(doc.text)
