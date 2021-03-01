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


ISO_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
ISO_TIME_FORMAT_SHORT = '%Y-%m-%d %H:%M:%S'


def _time_as_iso(tim):
    s = tim.strftime(ISO_TIME_FORMAT)
    return s[:-3] + 'Z'


def _time_from_iso(timestr):
    timestr = timestr[:-1]  # strip 'Z'
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT)


def _time_as_iso_short(tim):
    return tim.strftime(ISO_TIME_FORMAT_SHORT) + 'Z'


def _time_from_iso_short(timestr):
    timestr = timestr[:-1]  # strip 'Z'
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT_SHORT)


def _to_int(val: Optional[str]) -> Optional[int]:
    return int(val) if val is not None else None


class Acquisition:
    '''
    Data class, hold acquisition parameters for MPH
    '''
    _polarisation_mode: str = 'Q'                    # FIXED
    _polaristation_channels: str = 'HH, HV, VH, VV'  # FIXED
    _antenna_direction: str = 'LEFT'                 # FIXED

    def __init__(self):
        # L0, L1
        self.orbit_number: int = 1
        self.last_orbit_number: int = 1
        self.anx_date = datetime.datetime.now()
        self.start_time: int = 0                     # in ms since ANX
        self.completion_time: int = 0                # in ms since ANX
        self.instrument_config_id: int = 1
        self.orbit_drift_flag: bool = False
        self.repeat_cycle_id: str = '1'              # 1..7 or DR or __, refer to PDGS Products Naming Convention document
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


class MainProductHeader:
    '''
    This class is responsible for parsing and creating the Biomass Main Product Header (MPH).
    '''

    # Fixed for Biomass
    _platform_shortname = 'Biomass'
    _sensor_name = 'P-SAR'
    _sensor_type = 'RADAR'
    _browse_type = 'QUICKLOOK'
    _processing_mode = 'OPERATIONAL'

    def __init__(self):
        self._eop_identifier: Optional[str] = None
        self._begin_position: Optional[datetime.datetime] = None
        self._end_position: Optional[datetime.datetime] = None
        self._time_position: Optional[datetime.datetime] = None
        self._validity_start: Optional[datetime.datetime] = None
        self._validity_end: Optional[datetime.datetime] = None
        self._product_type: Optional[product_types.ProductType] = None
        self._product_baseline: Optional[int] = None
        self._processing_date: Optional[datetime.datetime] = None
        self._processor_name: Optional[str] = None
        self._processor_version: Optional[str] = None

        self.products = [
            {'file_name': 'product filename'},   # First product is mandatory and does not have the size/representation fields
            {'file_name': 'product filename', 'size': 100, 'representation': './schema/bio_l1_product.xsd'}
        ]
        self.doi = 'DOI'    # Digital Object Identifier
        self.acquisition_type = 'NOMINAL'   # OTHER, CALIBRATION or NOMINAL
        self.product_status = 'PLANNED'     # REJECTED, etc..
        self.processing_centre_code = 'ESR'
        self.processing_level = 'Other: L1'
        self.auxiliary_ds_file_names = ['AUX_ORB_Filename', 'AUX_ATT_Filename']
        self.biomass_source_product_ids = ['id']
        self.reference_documents = []

        # Raw only
        self._acquisition_station: Optional[str] = None
        self._acquisition_date: Optional[datetime.datetime] = None
        # Raw, HKTM only
        self.nr_transfer_frames = 0
        self.nr_transfer_frames_erroneous = 0
        self.nr_transfer_frames_corrupt = 0
        # Raw, science/ancillary only
        self._nr_instrument_source_packets = None
        self._nr_instrument_source_packets_erroneous = None
        self._nr_instrument_source_packets_corrupt = None

        # L0 only
        self.nr_l0_lines = '0,0'          # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.nr_l0_lines_missing = '0,0'  # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.nr_l0_lines_corrupt = '0,0'  # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.incomplete_l0_slice = False
        self.partial_l0_slice = False
        self.l1_frames_in_l0 = '0,1,2,4,5'

        # L1 only
        self.incomplete_l1_frame = False
        self.partial_l1_frame = False
        self.browse_ref_id = 'EPSG:4326'    # Or 'Unknown'
        self.browse_image_filename = 'browse image filename'

        # L0 and L1
        acquisition = Acquisition()
        self.acquisitions = [acquisition]
        self.tai_utc_diff = 0

        # L0, L1, L2a
        self.sensors = [{'type': self._sensor_type, 'mode': 'SM', 'swath_id': 'S1'}]  # Mode is SM, RO, EC, AC, swath is S1, S2, S3

        # L1, L2a
        self.footprint_polygon = '-8.015716 -63.764648 -6.809171 -63.251038 -6.967323 -62.789612 -8.176149 -63.278503 -8.015716 -63.764648'
        self.center_points = '-7.492090 -63.27095'

        for key, value in mph_namespaces.items():
            et.register_namespace(key, value)

    def get_product_type(self):
        return self._product_type.type

    def get_phenomenon_times(self):
        if self._begin_position is None or self._end_position is None:
            raise Exception('Times were not set')
        return self._begin_position, self._end_position

    def set_product_type(self, type: str, baseline: int):
        '''
        Type must be one of the predefined BIOMASS types
        '''
        product_type = product_types.find_product(type)
        if product_type is not None:
            self._product_type = product_type
            self.processing_level = 'other: {}'.format(product_type.level.upper())
            self._product_baseline = baseline
        else:
            raise Exception('Unknown product type {}'.format(type))

    def set_product_filename(self, filename: str):
        '''
        Must be the directory name (without path)
        '''
        self._eop_identifier = filename
        self.products[0] = {'file_name': filename}

    def set_phenomenon_times(self, start, end):
        '''
        Start/stop are UTC start date and time:
            - Acquisition sensing time for RAW, L0
            - Acquisition Zero Doppler Time for L1
            - Validity start time for AUX
            - Acquisition Zero Doppler Time, start of first image in the Stack for L2A
        '''
        self._begin_position = start
        self._end_position = end
        self._time_position = end  # = end, according to MPH definition

    def set_validity_times(self, start, end):
        '''
        Start/stop are UTC start date and time:
            - Acquisition sensing time for RAW_<PID>_<PC>, RAW___HKTM
            - Slice start time for RAWS<PID>_<PC>, L0
            - Frame start time for L1
            - Validity start time for AUX
            - Frame start time of first image in the Stack for *L2A
        '''
        self._validity_start = start
        self._validity_end = end

    def set_slice_nr(self, slice_nr: Optional[int]):
        '''
        For level0 products only. Slicenr may be None!
        '''
        self.acquisitions[0].slice_frame_nr = slice_nr

    def set_acquisition_date(self, acquisition_date):
        '''
        For raw products only
        '''
        self._acquisition_date = acquisition_date

    def set_acquisition_station(self, acquisition_station):
        '''
        For raw products only
        '''
        self._acquisition_station = acquisition_station

    def set_num_of_isp(self, num_isp, num_isp_erroneous, num_isp_corrupt):
        '''
        For raw products only
        '''
        self._nr_instrument_source_packets = num_isp
        self._nr_instrument_source_packets_erroneous = num_isp_erroneous
        self._nr_instrument_source_packets_corrupt = num_isp_corrupt

    def set_data_take_id(self, data_take_id):
        '''
        For AUT_ATT___, AUX_ORB___, L0, L1 products only
        '''
        self.acquisitions[0].data_take_id = data_take_id

    def set_num_of_lines(self, num_of_lines, num_of_lines_corrupt, num_of_lines_missing):
        '''
        For L0 product only
        '''
        self.nr_l0_lines = num_of_lines
        self.nr_l0_lines_corrupt = num_of_lines_corrupt
        self.nr_l0_lines_missing = num_of_lines_missing

    def set_processing_parameters(self, name: str, version: str, date: datetime.datetime):
        self._processor_name = name
        self._processor_version = version
        self._processing_date = date

    def _insert_time_period(self, parent, start, stop, id):
        # Insert TimePeriod element
        time_period = et.SubElement(parent, gml + 'TimePeriod')
        time_period.set(gml + 'id', self._eop_identifier + '_' + str(id))
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
        mph = et.Element(bio + 'EarthObservation')
        mph.set(gml + 'id', self._eop_identifier + '_1')

        phenomenon_time = et.SubElement(mph, om + 'phenomenonTime')
        self._insert_time_period(phenomenon_time, self._begin_position, self._end_position, 2)

        result_time = et.SubElement(mph, om + 'resultTime')
        time_instant = et.SubElement(result_time, gml + 'TimeInstant')
        time_instant.set(gml + 'id', self._eop_identifier + '_3')
        time_position = et.SubElement(time_instant, gml + 'timePosition')
        time_position.text = _time_as_iso(self._time_position)

        valid_time = et.SubElement(mph, om + 'validTime')
        self._insert_time_period(valid_time, self._validity_start, self._validity_end, 4)

        procedure = et.SubElement(mph, om + 'procedure')  # Procedure used to sense the data
        earth_observation_equipment = et.SubElement(procedure, eop + 'EarthObservationEquipment')  # Equipment used to sense the data
        earth_observation_equipment.set(gml + 'id', self._eop_identifier + '_5')
        platform = et.SubElement(earth_observation_equipment, eop + 'platform')  # Platform description
        Platform = et.SubElement(platform, eop + 'Platform')  # Nested element for platform description
        short_name = et.SubElement(Platform, eop + 'shortName')
        short_name.text = self._platform_shortname

        instrument = et.SubElement(earth_observation_equipment, eop + 'instrument')  # Instrument description
        Instrument = et.SubElement(instrument, eop + 'Instrument')  # Nested element for instrument description
        short_name = et.SubElement(Instrument, eop + 'shortName')
        short_name.text = self._sensor_name

        # Mandatory for L0, L1, L2A products
        if (self._product_type.level == 'l0' or self._product_type.level == 'l1' or self._product_type.level == 'l2a') and self.sensors:
            sensor = et.SubElement(earth_observation_equipment, eop + 'sensor')  # Sensor description
            Sensor = et.SubElement(sensor, eop + 'Sensor')  # Nested element for sensor description
            for s in self.sensors:
                sensor_type = et.SubElement(Sensor, eop + 'sensorType')
                sensor_type.text = s['type']
                sensor_mode = et.SubElement(Sensor, eop + 'operationalMode')
                sensor_mode.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:operationalMode')
                sensor_mode.text = s['mode']
                swath_id = et.SubElement(Sensor, eop + 'swathIdentifier')
                swath_id.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:swathIdentifier')
                swath_id.text = s['swath_id']

        # Mandatory for L0 and L1 products
        if self.acquisitions:
            acquisition_params = et.SubElement(earth_observation_equipment, eop + 'acquisitionParameters')
            acquisition = et.SubElement(acquisition_params, bio + 'Acquisition')
            for acq in self.acquisitions:
                et.SubElement(acquisition, eop + 'orbitNumber').text = str(acq.orbit_number)  # orbit start
                et.SubElement(acquisition, eop + 'lastOrbitNumber').text = str(acq.last_orbit_number)   # orbit stop
                et.SubElement(acquisition, eop + 'orbitDirection').text = acq.orbit_direction
                tracknr = et.SubElement(acquisition, eop + 'wrsLongitudeGrid')
                tracknr.text = str(acq.track_nr)
                tracknr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:relativeOrbits')
                framenr = et.SubElement(acquisition, eop + 'wrsLatitudeGrid')
                framenr.text = str(acq.slice_frame_nr) if acq.slice_frame_nr is not None else '___'
                framenr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:frames')
                et.SubElement(acquisition, eop + 'ascendingNodeDate').text = _time_as_iso(acq.anx_date)
                et.SubElement(acquisition, eop + 'startTimeFromAscendingNode', attrib={'uom': 'ms'}).text = str(acq.start_time)
                et.SubElement(acquisition, eop + 'completionTimeFromAscendingNode', attrib={'uom': 'ms'}).text = str(acq.completion_time)
                et.SubElement(acquisition, sar + 'polarisationMode').text = acq._polarisation_mode
                et.SubElement(acquisition, sar + 'polarisationChannels').text = acq._polaristation_channels
                et.SubElement(acquisition, sar + 'antennaLookDirection').text = acq._antenna_direction
                et.SubElement(acquisition, bio + 'missionPhase').text = acq.mission_phase
                et.SubElement(acquisition, bio + 'instrumentConfID').text = str(acq.instrument_config_id)
                et.SubElement(acquisition, bio + 'dataTakeID').text = str(acq.data_take_id)
                et.SubElement(acquisition, bio + 'orbitDriftFlag').text = str(acq.orbit_drift_flag).lower()
                et.SubElement(acquisition, bio + 'globalCoverageID').text = acq.global_coverage_id
                et.SubElement(acquisition, bio + 'majorCycleID').text = acq.major_cycle_id
                et.SubElement(acquisition, bio + 'repeatCycleID').text = acq.repeat_cycle_id

        observed_property = et.SubElement(mph, om + 'observedProperty')  # Observed property (Mandatory but empty)
        observed_property.set(xsi + 'nil', 'true')
        observed_property.set('nilReason', 'inapplicable')
        feature_of_interest = et.SubElement(mph, om + 'featureOfInterest')  # Observed area

        # Mandatory for L1, *L2A products
        if self._product_type.level == 'l1' or self._product_type.level == 'l2a':
            footprint = et.SubElement(feature_of_interest, eop + 'Footprint')
            footprint.set(gml + 'id', self._eop_identifier + '_6')
            multi_extent_of = et.SubElement(footprint, eop + 'multiExtentOf')  # Footprint representation structure, coordinates in posList
            multi_surface = et.SubElement(multi_extent_of, gml + 'MultiSurface')
            multi_surface.set(gml + 'id', self._eop_identifier + '_7')
            surface_member = et.SubElement(multi_surface, gml + 'surfaceMember')
            polygon = et.SubElement(surface_member, gml + 'Polygon')
            polygon.set(gml + 'id', self._eop_identifier + '_8')
            exterior = et.SubElement(polygon, gml + 'exterior')
            linear_ring = et.SubElement(exterior, gml + 'LinearRing')
            pos_list = et.SubElement(linear_ring, gml + 'posList')  # Footprint points
            pos_list.text = self.footprint_polygon
            center_of = et.SubElement(feature_of_interest, eop + 'centerOf')  # Acquisition centre representation structure
            point = et.SubElement(center_of, gml + 'Point')
            point.set(gml + 'id', self._eop_identifier + '_9')
            pos = et.SubElement(point, gml + 'pos')  # Coordinates of the centre of the acquisition
            pos.text = self.center_points

        result = et.SubElement(mph, om + 'result')  # Observation result
        earth_observation_result = et.SubElement(result, eop + 'EarthObservationResult')
        earth_observation_result.set(gml + 'id', self._eop_identifier + '_10')

        # Mandatory for L1 products
        if self._product_type.level == 'l1':
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
                et.SubElement(product_information, bio + 'rds').text = prod['representation']
            else:
                et.SubElement(product_information, eop + 'version').text = '{:02}'.format(self._product_baseline)

        meta_data_property = et.SubElement(mph, eop + 'metaDataProperty')  # Observation metadata
        earth_observation_meta_data = et.SubElement(meta_data_property, bio + 'EarthObservationMetaData')
        et.SubElement(earth_observation_meta_data, eop + 'identifier').text = self._eop_identifier
        et.SubElement(earth_observation_meta_data, eop + 'doi').text = self.doi  # Digital Object Identifier'
        et.SubElement(earth_observation_meta_data, eop + 'acquisitionType').text = self.acquisition_type
        # TODO: Write product type here? Ref says: "Describes product type in case that mixed types
        # are available within a single collection, this is ground segment specific definition"
        et.SubElement(earth_observation_meta_data, eop + 'productType').text = self._product_type.type
        et.SubElement(earth_observation_meta_data, eop + 'status').text = self.product_status

        # Mandatory for Raw data: Downlink information
        if self._product_type.level == 'raw':
            downlinked_to = et.SubElement(earth_observation_meta_data, eop + 'downlinkedTo')
            downlink_info = et.SubElement(downlinked_to, eop + 'DownlinkInformation')
            et.SubElement(downlink_info, eop + 'acquisitionStation').text = self._acquisition_station
            et.SubElement(downlink_info, eop + 'acquisitionDate').text = _time_as_iso(self._acquisition_date)

        processing = et.SubElement(earth_observation_meta_data, eop + 'processing')  # Data processing information
        processing_info = et.SubElement(processing, bio + 'ProcessingInformation')
        proc_center = et.SubElement(processing_info, eop + 'processingCenter')
        proc_center.text = self.processing_centre_code
        proc_center.set('codeSpace', 'urn:esa:eop:Biomass:facility')
        et.SubElement(processing_info, eop + 'processingDate').text = _time_as_iso_short(self._processing_date)
        et.SubElement(processing_info, eop + 'processorName').text = self._processor_name
        et.SubElement(processing_info, eop + 'processorVersion').text = self._processor_version
        et.SubElement(processing_info, eop + 'processingLevel').text = self.processing_level

        if not self._product_type.level == 'aux':
            for name in self.auxiliary_ds_file_names:
                et.SubElement(processing_info, eop + 'auxiliaryDataSetFileName').text = name

        et.SubElement(processing_info, eop + 'processingMode', attrib={'codespace': 'urn:esa:eop:Biomass:class'}).text = self._processing_mode

        if self._product_type.level == 'l0' or self._product_type.level == 'l1' or self._product_type.level == '2a':
            for id in self.biomass_source_product_ids:
                et.SubElement(processing_info, bio + 'sourceProduct').text = id

        if self._product_type.level == 'l0' or self._product_type.level == 'l1':
            et.SubElement(earth_observation_meta_data, bio + 'TAI-UTC').text = str(self.tai_utc_diff)

        if self._product_type.level == 'raw':
            if self._product_type.type == 'RAW___HKTM':
                et.SubElement(earth_observation_meta_data, bio + 'numOfTFs').text = str(self.nr_transfer_frames)
                et.SubElement(earth_observation_meta_data, bio + 'numOfTFsWithErrors').text = str(self.nr_transfer_frames_erroneous)
                et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedTFs').text = str(self.nr_transfer_frames_corrupt)
            else:
                et.SubElement(earth_observation_meta_data, bio + 'numOfISPs').text = str(self._nr_instrument_source_packets)
                et.SubElement(earth_observation_meta_data, bio + 'numOfISPsWithErrors').text = str(self._nr_instrument_source_packets_erroneous)
                et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedISPs').text = str(self._nr_instrument_source_packets_corrupt)

        if self._product_type.level == 'l0':
            et.SubElement(earth_observation_meta_data, bio + 'numOfLines').text = self.nr_l0_lines
            et.SubElement(earth_observation_meta_data, bio + 'numOfMissingLines').text = self.nr_l0_lines_missing
            et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedLines').text = self.nr_l0_lines_corrupt
            et.SubElement(earth_observation_meta_data, bio + 'incompleteSlice').text = str(self.incomplete_l0_slice).lower()
            et.SubElement(earth_observation_meta_data, bio + 'partialSlice').text = str(self.partial_l0_slice).lower()
            et.SubElement(earth_observation_meta_data, bio + 'framesList').text = self.l1_frames_in_l0

        if self._product_type.level == 'l1':
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
        self._begin_position, self._end_position = self._parse_time_period(phenomenon_time, 2)

        result_time = root.find(om + 'resultTime')
        time_instant = result_time.find(gml + 'TimeInstant')
        # time_instant.set(gml + 'id', self.eop_identifier + '_3')
        self._time_position = _time_from_iso(time_instant.findtext(gml + 'timePosition', ''))

        valid_time = root.find(om + 'validTime')
        self._validity_start, self._validity_end = self._parse_time_period(valid_time, 4)

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
        self.sensors.clear()
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
                self.sensors.append(s)

        # Mandatory for L0 and L1 products
        self.acquisitions.clear()
        acquisition_params = earth_observation_equipment.find(eop + 'acquisitionParameters')
        if acquisition_params is not None:
            for acquisition in acquisition_params.findall(bio + 'Acquisition'):
                acq = Acquisition()
                acq.orbit_number = int(acquisition.findtext(eop + 'orbitNumber', '0'))
                acq.last_orbit_number = int(acquisition.findtext(eop + 'lastOrbitNumber', '0'))
                acq.orbit_direction = acquisition.findtext(eop + 'orbitDirection', '')
                acq.track_nr = int(acquisition.findtext(eop + 'wrsLongitudeGrid', '0'))
                # tracknr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:relativeOrbits')
                nr = acquisition.findtext(eop + 'wrsLatitudeGrid', '')
                acq.slice_frame_nr = int(nr) if not nr == '___' else None
                # framenr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:frames')
                acq.anx_date = _time_from_iso(acquisition.findtext(eop + 'ascendingNodeDate'))
                acq.start_time = int(acquisition.findtext(eop + 'startTimeFromAscendingNode', '0'))    # TODO ={'uom': 'ms'}
                acq.completion_time = int(acquisition.findtext(eop + 'completionTimeFromAscendingNode', '0'))  # TODO ={'uom': 'ms'}
                acq._polarisation_mode = acquisition.findtext(sar + 'polarisationMode', '')
                acq._polaristation_channels = acquisition.findtext(sar + 'polarisationChannels', '')
                acq._antenna_direction = acquisition.findtext(sar + 'antennaLookDirection', '')
                acq.mission_phase = acquisition.findtext(bio + 'missionPhase', '')
                acq.instrument_config_id = int(acquisition.findtext(bio + 'instrumentConfID', '0'))
                acq.data_take_id = int(acquisition.findtext(bio + 'dataTakeID', ''))
                acq.orbit_drift_flag = acquisition.findtext(bio + 'orbitDriftFlag', '').lower() == 'true'
                acq.global_coverage_id = acquisition.findtext(bio + 'globalCoverageID', '')
                acq.major_cycle_id = acquisition.findtext(bio + 'majorCycleID', '')
                acq.repeat_cycle_id = acquisition.findtext(bio + 'repeatCycleID', '')
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
            center_of = feature_of_interest.find(eop + 'centerOf')  # Acquisition centre representation structure
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
                self._product_baseline = int(version)
                self.products.append({'file_name': file_name})
            else:
                size = int(product_information.findtext(eop + 'size', '0'))  # attrib={'uom': 'bytes'}
                representation = product_information.findtext(bio + 'rds')
                self.products.append({'file_name': file_name, 'size': size, 'representation': representation})

        meta_data_property = root.find(eop + 'metaDataProperty')  # Observation metadata
        earth_observation_meta_data = meta_data_property.find(bio + 'EarthObservationMetaData')
        self._eop_identifier = earth_observation_meta_data.findtext(eop + 'identifier')
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
            self._acquisition_station = downlink_info.findtext(eop + 'acquisitionStation')
            self._acquisition_date = _time_from_iso(downlink_info.findtext(eop + 'acquisitionDate'))

        processing = earth_observation_meta_data.find(eop + 'processing')  # Data processing information
        processing_info = processing.find(bio + 'ProcessingInformation')
        self.processing_centre_code = processing_info.findtext(eop + 'processingCenter')
        # proc_center.set('codeSpace', 'urn:esa:eop:Biomass:facility')
        self._processing_date = _time_from_iso_short(processing_info.findtext(eop + 'processingDate'))
        self._processor_name = processing_info.findtext(eop + 'processorName')
        self._processor_version = processing_info.findtext(eop + 'processorVersion')
        self.processing_level = processing_info.findtext(eop + 'processingLevel')

        self.auxiliary_ds_file_names.clear()
        for proc_info in processing_info.findall(eop + 'auxiliaryDataSetFileName'):
            if proc_info.text is not None:
                self.auxiliary_ds_file_names.append(proc_info.text)

        self._processing_mode = processing_info.find(eop + 'processingMode').text    # attrib={'codespace': 'urn:esa:eop:Biomass:class'}

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

        self._nr_instrument_source_packets = _to_int(earth_observation_meta_data.findtext(bio + 'numOfISPs'))
        self._nr_instrument_source_packets_erroneous = _to_int(earth_observation_meta_data.findtext(bio + 'numOfISPsWithErrors'))
        self._nr_instrument_source_packets_corrupt = _to_int(earth_observation_meta_data.findtext(bio + 'numOfCorruptedISPs'))

        # Mandatory for level 0. Note: these are all pairs of numbers
        self.nr_l0_lines = earth_observation_meta_data.findtext(bio + 'numOfLines')
        self.nr_l0_lines_missing = earth_observation_meta_data.findtext(bio + 'numOfMissingLines')
        self.nr_l0_lines_corrupt = earth_observation_meta_data.findtext(bio + 'numOfCorruptedLines')
        self.incomplete_l0_slice = earth_observation_meta_data.findtext(bio + 'incompleteSlice')
        self.partial_l0_slice = earth_observation_meta_data.findtext(bio + 'partialSlice')
        self.l1_frames_in_l0 = earth_observation_meta_data.findtext(bio + 'framesList')

        # Level 1
        self.incomplete_l1_frame = earth_observation_meta_data.findtext(bio + 'incompleteFrame')
        self.partial_l1_frame = earth_observation_meta_data.findtext(bio + 'partialFrame')

        self.reference_documents.clear()
        for doc in earth_observation_meta_data.findall(bio + 'refDoc'):
            if doc.text is not None:
                self.reference_documents.append(doc.text)
