'''
Copyright (C) 2021-2023 S[&]T, The Netherlands.

Parse and generate Flex Main Product Headers.
Ref: ESA-EOPG-EOEP-TN-0025

TODO:
- Product URI
- Product size
- acquisitionType
- Product status
'''

import datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as et

from procsim.core import utils
from procsim.core.exceptions import ParseError, ScenarioError

from . import product_types


mph_namespaces = {
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
    'ows': "http://www.opengis.net/ows/2.0",
    'sar': "http://www.opengis.net/sar/2.1",
    'xlink': "http://www.w3.org/1999/xlink",
    'om': "http://www.opengis.net/om/2.0",
    'gml': "http://www.opengis.net/gml/3.2",
    'eop': "http://www.opengis.net/eop/2.1",
    'opt': "http://www.opengis.net/opt/2.1",
}

# for ns, url in mph_namespaces.items():
#     locals()[ns] = "{%s}" % url
# Write in full, to avoid pylance warnings...
xsi = "{%s}" % mph_namespaces['xsi']
opt = "{%s}" % mph_namespaces['opt']
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
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT).replace(tzinfo=datetime.timezone.utc)


def _time_as_iso_short(tim: datetime.datetime) -> str:
    return tim.strftime(ISO_TIME_FORMAT_SHORT) + 'Z'


def _time_from_iso_short(timestr: Optional[str]) -> Optional[datetime.datetime]:
    if timestr is None:
        return None
    timestr = timestr[:-1]  # strip 'Z'
    return datetime.datetime.strptime(timestr, ISO_TIME_FORMAT_SHORT).replace(tzinfo=datetime.timezone.utc)


def _to_int(val: Optional[str]) -> Optional[int]:
    try:
        return int(val) if val else None
    except ValueError:
        return None


def _to_bool(val: Optional[str]) -> Optional[bool]:
    return None if val is None else True if val == 'true' else False if val == 'false' else None


class Acquisition:
    '''
    Hold acquisition parameters for MPH
    '''

    def __init__(self):
        self.orbit_number = 1
        self.last_orbit_number = 1
        self.orbit_direction = 'ASCENDING'
        self.illumination_azimuth_angle = 10.2
        self.across_track_incidence_angle = -14.0
        self.along_track_incidentce_angle = -13.9
        self.pitch = 0
        self.roll = 0
        self.yaw = 0

    def __eq__(self, other):  # called from tests
        return self.__dict__ == other.__dict__


class MainProductHeader:
    '''
    This class is responsible for parsing and creating the FLEX Main Product Header (MPH).
    '''

    # Fixed for Flex
    _platform_shortname = 'FLEX'
    _sensor_name = 'FLORIS'
    _sensor_type = 'OPTICAL'
    _browse_type = 'QUICKLOOK'
    processing_mode = 'NOMINAL'

    def __init__(self):
        # These parameters MUST be set (no defaults)
        self.eop_identifier: Optional[str] = None
        self.begin_position: Optional[datetime.datetime] = None
        self.end_position: Optional[datetime.datetime] = None
        self.time_position: Optional[datetime.datetime] = None
        self.validity_start: Optional[datetime.datetime] = None
        self.validity_stop: Optional[datetime.datetime] = None
        self.product_baseline: Optional[str] = None
        self.processing_date: Optional[datetime.datetime] = None
        self.processor_name: Optional[str] = None
        self.processor_version: Optional[str] = None

        self.data_take_id: Optional[int] = None
        self.slice_frame_nr: Optional[int] = None
        self.along_track_coordinate: Optional[int] = None
        self.calibration_id: Optional[int] = None
        self.mission_phase: Optional[str] = None
        self.anx_elapsed: Optional[float] = None
        self.apid: Optional[str] = None

        self._product_type_info: Optional[product_types.ProductType] = None
        self._processing_level = 'Other: L1'

        self.products: List[Dict[str, Any]] = [
            {'file_name': 'product filename'},   # First product is mandatory and does not have the size/representation fields
        ]
        self.doi = '10.5270/FLX-xxxxxxx'    # Digital Object Identifier
        self.acquisition_type = 'NOMINAL'   # OTHER, CALIBRATION or NOMINAL
        self.acquisition_subtype = None     # set for CALIBRATION
        self.product_status = 'ARCHIVED'     # REJECTED, etc..
        self.product_status_subtype = 'ON-LINE'
        self.processing_centre_code = 'ESR'
        self.downlink_station_code = 'KSE'
        self.archive_station_code = 'ESR'
        self.auxiliary_ds_file_names = []  # TODO l1 or higher or 'not needed' in spec?
        self.reference_documents = []

        self.completeness_assesment: Optional[str] = None
        self.slice_start_position: Optional[str] = None
        self.slice_stop_position: Optional[str] = None

        self.sensor_detector: Optional[str] = None

        self.relative_orbit_number = None
        self.cycle_number = None

        # Raw only
        self.acquisition_station: Optional[str] = None
        self.acquisition_date: Optional[datetime.datetime] = None

        # Raw, HKTM only
        self.nr_transfer_frames: Optional[int] = 0
        self.nr_transfer_frames_erroneous: Optional[int] = 0
        self.nr_transfer_frames_corrupt: Optional[int] = 0

        # Raw, science/ancillary only
        self.nr_instrument_source_packets: Optional[int] = 0
        self.nr_instrument_source_packets_erroneous: Optional[int] = 0
        self.nr_instrument_source_packets_corrupt: Optional[int] = 0

        # L1 only
        self.browse_ref_id: Optional[str] = 'Unknown'
        self.browse_image_filename: Optional[str] = ''

        # L0 and L1
        acquisition = Acquisition()
        self.acquisitions = [acquisition]

        # L0, L1, L2a
        self.sensor_mode = None

        # L1, L2a
        self.footprint_polygon: Optional[str] = None
        self.center_points: Optional[str] = None

        for key, value in mph_namespaces.items():
            et.register_namespace(key, value)

    def __eq__(self, other):  # called from tests
        return self.__dict__ == other.__dict__

    @property
    def product_type(self):
        if self._product_type_info is None:
            return ''
        return self._product_type_info.type

    @product_type.setter
    def product_type(self, type: str):
        '''
        Type must be one of the predefined FLEX types
        '''
        product_type_info = product_types.find_product(type)
        if product_type_info is not None:
            self._product_type_info = product_type_info
            self._processing_level = 'other: {}'.format(product_type_info.level.upper())
        else:
            raise ScenarioError('Unknown product type {}'.format(type))

    def initialize_product_list(self, filename: str):
        '''
        Must be the directory name (without path)
        '''
        self.eop_identifier = filename

        self.products.clear()
        self.products.append({'file_name': filename})

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

    def set_processing_parameters(self, name: str, version: str):
        self.processor_name = name
        self.processor_version = version

    def _insert_time_period(self, parent, start: datetime.datetime, stop: datetime.datetime, id):
        # Insert TimePeriod element
        time_period = et.SubElement(parent, gml + 'TimePeriod')
        if self.eop_identifier is None:
            raise ParseError(self.eop_identifier)
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

    def append_file(self, product_path: str, size_mb: Optional[int] = None, representation_path: Optional[str] = None) -> None:
        self.products.append({
            'file_name': product_path,
            'size': None if size_mb is None else size_mb * 2**20,
            'representation': representation_path
        })

    def write(self, file_name):
        # Create MPH and write to file (TODO: split in generate and write methods?)
        if self._product_type_info is None:
            raise ParseError(self._product_type_info)
        level = self._product_type_info.level

        mph = et.Element(opt + 'EarthObservation')
        if self.eop_identifier is None:
            raise ParseError(self.eop_identifier)
        mph.set(gml + 'id', self.eop_identifier + '_1')

        # Some parameters have no default and MUST be set prior to generation
        if self.begin_position is None or self.end_position is None:
            raise ScenarioError('Begin/end position must be set before creating MPH')
        if self.validity_start is None or self.validity_stop is None:
            raise ScenarioError('Validity start/stop must be set before creating MPH')
        if not self.eop_identifier:
            raise ScenarioError('The eop_identifier (file name) must be set before creating MPH')

        # By convention, time_position is equal to end_position
        self.time_position = self.end_position

        phenomenon_time = et.SubElement(mph, om + 'phenomenonTime')
        self._insert_time_period(phenomenon_time, self.begin_position, self.end_position, 2)

        result_time = et.SubElement(mph, om + 'resultTime')
        time_instant = et.SubElement(result_time, gml + 'TimeInstant')
        time_instant.set(gml + 'id', self.eop_identifier + '_3')
        time_position = et.SubElement(time_instant, gml + 'timePosition')
        time_position.text = _time_as_iso(self.time_position)

        procedure = et.SubElement(mph, om + 'procedure')  # Procedure used to sense the data
        earth_observation_equipment = et.SubElement(procedure, eop + 'EarthObservationEquipment')  # Equipment used to sense the data
        earth_observation_equipment.set(gml + 'id', self.eop_identifier + '_4')
        platform = et.SubElement(earth_observation_equipment, eop + 'platform')  # Platform description
        Platform = et.SubElement(platform, eop + 'Platform')  # Nested element for platform description
        short_name = et.SubElement(Platform, eop + 'shortName')
        short_name.text = self._platform_shortname

        instrument = et.SubElement(earth_observation_equipment, eop + 'instrument')  # Instrument description
        Instrument = et.SubElement(instrument, eop + 'Instrument')  # Nested element for instrument description
        short_name = et.SubElement(Instrument, eop + 'shortName')
        short_name.text = self._sensor_name

        # Mandatory for L0, L1, L2A products
        sensors = [{'type': self._sensor_type, 'mode': self.sensor_mode}]
        if (level == 'l0' or level == 'l1' or level == 'l2a'):
            sensor = et.SubElement(earth_observation_equipment, eop + 'sensor')  # Sensor description
            Sensor = et.SubElement(sensor, eop + 'Sensor')  # Nested element for sensor description
            for s in sensors:
                sensor_type = et.SubElement(Sensor, eop + 'sensorType')
                sensor_type.text = s['type']
                sensor_mode = et.SubElement(Sensor, eop + 'operationalMode')
                sensor_mode.set('codeSpace', 'urn:esa:eop:FLORIS:operationalMode')
                sensor_mode.text = s['mode']

        if level in ['raws', 'l0', 'l1', 'l2a']:
            acquisition_params = et.SubElement(earth_observation_equipment, eop + 'acquisitionParameters')
            acquisition = et.SubElement(acquisition_params, eop + 'Acquisition')
            for acq in self.acquisitions:
                et.SubElement(acquisition, eop + 'orbitNumber').text = str(acq.orbit_number)
                et.SubElement(acquisition, eop + 'lastOrbitNumber').text = str(acq.last_orbit_number)
                et.SubElement(acquisition, eop + 'orbitDirection').text = acq.orbit_direction
                et.SubElement(acquisition, eop + 'illuminationAzimuthAngle', attrib={'uom': 'deg'}).text = '10.2'
                et.SubElement(acquisition, eop + 'acrossTrackIncidenceAngle', attrib={'uom': 'deg'}).text = '-14.0'
                et.SubElement(acquisition, eop + 'alongTrackIncidenceAngle', attrib={'uom': 'deg'}).text = '-13.9'
                et.SubElement(acquisition, eop + 'pitch', attrib={'uom': 'deg'}).text = '0'
                et.SubElement(acquisition, eop + 'rol', attrib={'uom': 'deg'}).text = '0'
                et.SubElement(acquisition, eop + 'yaw', attrib={'uom': 'deg'}).text = '0'

        observed_property = et.SubElement(mph, om + 'observedProperty')  # Observed property (Mandatory but empty)
        observed_property.set(xsi + 'nil', 'true')
        observed_property.set('nilReason', 'inapplicable')
        feature_of_interest = et.SubElement(mph, om + 'featureOfInterest')  # Observed area

        result = et.SubElement(mph, om + 'result')  # Observation result
        earth_observation_result = et.SubElement(result, eop + 'EarthObservationResult')
        earth_observation_result.set(gml + 'id', self.eop_identifier + '_9')

        for prod in self.products:
            product = et.SubElement(earth_observation_result, eop + 'product')
            product_information = et.SubElement(product, eop + 'ProductInformation')
            self._insert_file_name(product_information, prod['file_name'])
            if prod.get('size') is not None:
                et.SubElement(product_information, eop + 'size', attrib={'uom': 'bytes'}).text = str(prod['size'])
                if prod.get('representation') is not None:    # Mandatory for if type is XML
                    et.SubElement(product_information, eop + 'rds').text = prod['representation']
            else:
                et.SubElement(product_information, eop + 'version').text = self.product_baseline
                et.SubElement(product_information, eop + 'timeliness').text = 'NOMINAL'  # TODO CALIBRATION?

        meta_data_property = et.SubElement(mph, eop + 'metaDataProperty')  # Observation metadata
        earth_observation_meta_data = et.SubElement(meta_data_property, eop + 'EarthObservationMetaData')
        et.SubElement(earth_observation_meta_data, eop + 'identifier').text = self.eop_identifier
        et.SubElement(earth_observation_meta_data, eop + 'creationDate').text = _time_as_iso(datetime.datetime.now())
        et.SubElement(earth_observation_meta_data, eop + 'doi').text = self.doi  # Digital Object Identifier
        et.SubElement(earth_observation_meta_data, eop + 'acquisitionType').text = self.acquisition_type
        if self.acquisition_subtype is not None:
            act = et.SubElement(earth_observation_meta_data, eop + 'acquisitionSubType')
            act.text = self.acquisition_subtype
            act.set('codeSpace', 'urn:esa:eop:FLEX:acquisitionSubTypes')

        # TODO: Write product type here? Ref says: "Describes product type in case that mixed types
        # are available within a single collection, this is ground segment specific definition"
        et.SubElement(earth_observation_meta_data, eop + 'productType').text = self.product_type
        et.SubElement(earth_observation_meta_data, eop + 'status').text = self.product_status
        et.SubElement(earth_observation_meta_data, eop + 'statusSubType').text = self.product_status_subtype

        if level in ['raw']:
            if self.acquisition_date is None:
                raise ScenarioError('Acquisition time must be set prior to generating MPH')
            if self.acquisition_station is None:
                raise ScenarioError('Acquisition station must be set prior to generating MPH')

            downlinked_to = et.SubElement(earth_observation_meta_data, eop + 'downlinkedTo')
            downlink_info = et.SubElement(downlinked_to, eop + 'DownlinkInformation')
            acq_station = et.SubElement(downlink_info, eop + 'acquisitionStation')
            acq_station.text = self.downlink_station_code
            acq_station.set('codeSpace', 'urn:esa:eop:FLEX:stationCode')
            et.SubElement(downlink_info, eop + 'acquisitionDate').text = _time_as_iso(self.acquisition_date)

            archived_in = et.SubElement(earth_observation_meta_data, eop + 'archivedIn')
            archive_info = et.SubElement(archived_in, eop + 'ArchivingInformation')
            arch_center = et.SubElement(archive_info, eop + 'archivingCenter')
            arch_center.text = self.archive_station_code
            arch_center.set('codeSpace', 'urn:esa:eop:FLEX:stationCode')
            et.SubElement(archive_info, eop + 'archivingDate').text = _time_as_iso(self.acquisition_date)

        qc_degradation = et.SubElement(earth_observation_meta_data, eop + 'productQualityDegradation')
        qc_degradation.set('uom', '%')
        qc_degradation.text = '25'

        et.SubElement(earth_observation_meta_data, eop + 'productQualityDegradationQuotationMode').text = 'AUTOMATIC'
        et.SubElement(earth_observation_meta_data, eop + 'productQualityStatus').text = 'DEGRADED'

        # only if productQualityStatus is DEGRADED!
        qc_degradation_tag = et.SubElement(earth_observation_meta_data, eop + 'productQualityDegradationTag')
        qc_degradation_tag.set('codeSpace', 'urn:esa:eop:FLEX:qcDegradationTags')
        qc_degradation_tag.text = 'RADIOMETRIC'

        et.SubElement(earth_observation_meta_data, eop + 'ProductQualityReportURL').text = 'http://xxx/xxx/xxx.pdf'

        processing = et.SubElement(earth_observation_meta_data, eop + 'processing')  # Data processing information
        processing_info = et.SubElement(processing, eop + 'ProcessingInformation')
        proc_center = et.SubElement(processing_info, eop + 'processingCenter')
        proc_center.text = self.processing_centre_code
        proc_center.set('codeSpace', 'urn:esa:eop:FLEX:facility')
        if self.processing_date is None or self.processor_name is None or \
                self.processor_version is None or self._processing_level is None:
            raise ScenarioError('Processing parameters must be set prior to generating MPH')
        et.SubElement(processing_info, eop + 'processingDate').text = _time_as_iso_short(self.processing_date)
        et.SubElement(processing_info, eop + 'processorName').text = self.processor_name
        et.SubElement(processing_info, eop + 'processorVersion').text = self.processor_version
        et.SubElement(processing_info, eop + 'processingLevel').text = self._processing_level

        if level == 'aux':
            et.SubElement(processing_info, eop + 'nativeProductFormat').text = 'xml'
        else:
            et.SubElement(processing_info, eop + 'nativeProductFormat').text = 'dat'

        if level not in ['aux']:
            for name in self.auxiliary_ds_file_names:
                et.SubElement(processing_info, eop + 'auxiliaryDataSetFileName').text = name

        et.SubElement(processing_info, eop + 'processingMode').text = self.processing_mode

        # add vendor-specific metadata
        def add_vendor_specific(attr, value):
            if value is not None:
                value = str(value)
                vendor_specific = et.SubElement(earth_observation_meta_data, eop + 'vendorSpecific')
                specific_information = et.SubElement(vendor_specific, eop + 'SpecificInformation')
                et.SubElement(specific_information, eop + 'localAttribute').text = attr
                et.SubElement(specific_information, eop + 'localValue').text = value

        if level != 'raw':
            add_vendor_specific('missionPhase', self.mission_phase)
            add_vendor_specific('Ref_Doc', 'Product_Definition_Format_xx.yy')  # TODO fill in ref_doc, task_table stuff?
            add_vendor_specific('Task_Table_Name', 'Task Table Name')
            add_vendor_specific('Task_Table_Version', 'xx.yy')
            add_vendor_specific('Duration', '%.3f' % (self.end_position - self.begin_position).total_seconds())
            add_vendor_specific('Cycle_Number', self.cycle_number)
            add_vendor_specific('Relative_Orbit_Number', self.relative_orbit_number)
            add_vendor_specific('dataTakeID', self.data_take_id)
            add_vendor_specific('calibrationID', self.calibration_id)
            add_vendor_specific('slicingGridFrameNumber', self.slice_frame_nr)
            add_vendor_specific('alongtrackCoordinate', self.along_track_coordinate)
            if self.anx_elapsed is not None:
                add_vendor_specific('ANX_elapsed_time', '%.3f' % self.anx_elapsed)
            add_vendor_specific('Baseline', self.product_baseline)
        if level in ('raw', 'raws'):
            add_vendor_specific('numOfISPs', self.nr_instrument_source_packets)
            add_vendor_specific('numOfISPsWithErrors', self.nr_instrument_source_packets_erroneous)
            add_vendor_specific('numOfCorruptedISPs', self.nr_instrument_source_packets_corrupt)
            add_vendor_specific('numOfTFs', self.nr_transfer_frames)
            add_vendor_specific('numOfTFsWithErrors', self.nr_transfer_frames_erroneous)
            add_vendor_specific('numOfCorruptedTFs', self.nr_transfer_frames_corrupt)
        if level == 'raws':
            add_vendor_specific('apid', self.apid)
            add_vendor_specific('sensorDetector', self.sensor_detector)
            add_vendor_specific('completenessAssesment', self.completeness_assesment)
        if level in ('raws', 'l0'):
            add_vendor_specific('sliceStartPosition', self.slice_start_position)
            add_vendor_specific('sliceStopPosition', self.slice_stop_position)

        # Create XML
        tree = et.ElementTree(mph)
        utils.indent_xml(tree.getroot())
        tree.write(file_name, xml_declaration=True, encoding='utf-8')

    def parse(self, file_name):  # TODO update for changes in writer..
        '''Open MPH file and parse contents. Does not check for ID's.'''
        tree = et.parse(file_name)
        root = tree.getroot()
        phenomenon_time = root.find(om + 'phenomenonTime')
        begin_position, end_position = self._parse_time_period(phenomenon_time, 2)
        if begin_position is None:
            raise ParseError(begin_position)
        if end_position is None:
            raise ParseError(end_position)
        self.begin_position, self.end_position = begin_position, end_position

        result_time = root.find(om + 'resultTime')
        if result_time is None:
            raise ParseError(result_time)
        time_instant = result_time.find(gml + 'TimeInstant')
        # time_instant.set(gml + 'id', self.eop_identifier + '_3')
        if time_instant is None:
            raise ParseError(time_instant)
        time_position = _time_from_iso(time_instant.findtext(gml + 'timePosition'))
        if time_position is None:
            raise ParseError(time_position)
        self.time_position = time_position

        procedure = root.find(om + 'procedure')  # Procedure used to sense the data
        if procedure is None:
            raise ParseError(procedure)
        earth_observation_equipment = procedure.find(eop + 'EarthObservationEquipment')  # Equipment used to sense the data
        # earth_observation_equipment.set(gml + 'id', self.eop_identifier + '_5')
        if earth_observation_equipment is None:
            raise ParseError(earth_observation_equipment)
        platform = earth_observation_equipment.find(eop + 'platform')  # Platform description
        if platform is None:
            raise ParseError(platform)
        Platform = platform.find(eop + 'Platform')  # Nested element for platform description
        if Platform is None:
            raise ParseError(Platform)
        self._platform_shortname = Platform.findtext(eop + 'shortName')

        instrument = earth_observation_equipment.find(eop + 'instrument')  # Instrument description
        if instrument is None:
            raise ParseError(instrument)
        Instrument = instrument.find(eop + 'Instrument')  # Nested element for instrument description
        if Instrument is None:
            raise ParseError(Instrument)
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
                # sensor_mode.set('codeSpace', 'urn:esa:eop:FLORIS:operationalMode')
                sensors.append(s)

        # Assume there are 0 or 1 sensors
        if sensors:
            self.sensor_mode = sensors[0]['mode']

        acquisition_params = earth_observation_equipment.find(eop + 'acquisitionParameters')
        if acquisition_params is not None:
            # TODO: Clear the list. Drawback: existing values are gone now. Other option is to
            # overwrite the existing values and append new acquisitions if there are more.
            self.acquisitions.clear()
            for acquisition in acquisition_params.findall(eop + 'Acquisition'):
                acq = Acquisition()
                acq.orbit_number = _to_int(acquisition.findtext(eop + 'orbitNumber')) or acq.orbit_number
                acq.last_orbit_number = _to_int(acquisition.findtext(eop + 'lastOrbitNumber')) or acq.last_orbit_number
                acq.orbit_direction = acquisition.findtext(eop + 'orbitDirection') or acq.orbit_direction
                self.acquisitions.append(acq)

        # observed_property = root.find(om + 'observedProperty')  # Observed property (Mandatory but empty)
        # observed_property.set(xsi + 'nil', 'true')
        # observed_property.set('nilReason', 'inapplicable')
        feature_of_interest = root.find(om + 'featureOfInterest')  # Observed area
        if feature_of_interest is None:
            raise ParseError(feature_of_interest)

        # Mandatory for L1, *L2A products
        footprint = feature_of_interest.find(eop + 'Footprint')
        if footprint is not None:
            # footprint.set(gml + 'id', self.eop_identifier + '_6')
            multi_extent_of = footprint.find(eop + 'multiExtentOf')  # Footprint representation structure, coordinates in posList
            if multi_extent_of is None:
                raise ParseError(multi_extent_of)
            multi_surface = multi_extent_of.find(gml + 'MultiSurface')
            if multi_surface is None:
                raise ParseError(multi_surface)
            # multi_surface.set(gml + 'id', self.eop_identifier + '_7')
            surface_member = multi_surface.find(gml + 'surfaceMember')
            if surface_member is None:
                raise ParseError(surface_member)
            polygon = surface_member.find(gml + 'Polygon')
            if polygon is None:
                raise ParseError(polygon)
            # polygon.set(gml + 'id', self.eop_identifier + '_8')
            exterior = polygon.find(gml + 'exterior')
            if exterior is None:
                raise ParseError(exterior)
            linear_ring = exterior.find(gml + 'LinearRing')
            if linear_ring is None:
                raise ParseError(linear_ring)
            self.footprint_polygon = linear_ring.findtext(gml + 'posList')  # Footprint points

            #
            # TODO! This is a discrepancy between spec and example!!
            #

            # center_of = feature_of_interest.find(eop + 'centerOf')  # Acquisition centre representation structure
            center_of = footprint.find(eop + 'centerOf')  # Acquisition centre representation structure
            if center_of is None:
                raise ParseError(center_of)

            point = center_of.find(gml + 'Point')
            if point is None:
                raise ParseError(point)
            # point.set(gml + 'id', self.eop_identifier + '_9')
            self.center_points = point.findtext(gml + 'pos')  # Coordinates of the centre of the acquisition

        result = root.find(om + 'result')  # Observation result
        if result is None:
            raise ParseError(result)
        earth_observation_result = result.find(eop + 'EarthObservationResult')
        if earth_observation_result is None:
            raise ParseError(earth_observation_result)
        # earth_observation_result.set(gml + 'id', self.eop_identifier + '_10')

        # Mandatory for L1 products
        browse = earth_observation_result.find(eop + 'browse')
        if browse is not None:
            browse_info = browse.find(eop + 'BrowseInformation')
            if browse_info is None:
                raise ParseError(browse_info)
            self._browse_type = browse_info.findtext(eop + 'type')
            self.browse_ref_id = browse_info.findtext(eop + 'referenceSystemIdentifier')  # Coordinate reference system name
            # browse_ref_id.set('codeSpace', 'urn:esa:eop:crs')
            # self._insert_file_name(browse_info, self.browse_image_filename)
            self.browse_image_filename = self._parse_file_name(browse_info)

        self.products.clear()
        for product in earth_observation_result.findall(eop + 'product'):
            product_information = product.find(eop + 'ProductInformation')
            if product_information is None:
                raise ParseError(product_information)
            file_name = self._parse_file_name(product_information)
            version = product_information.findtext(eop + 'version')
            if version is not None:
                self.product_baseline = version
                self.products.append({'file_name': file_name})
            else:
                size = int(product_information.findtext(eop + 'size', '0'))  # attrib={'uom': 'bytes'}
                representation = product_information.findtext(eop + 'rds')
                self.products.append({'file_name': file_name, 'size': size, 'representation': representation})

        meta_data_property = root.find(eop + 'metaDataProperty')  # Observation metadata
        if meta_data_property is None:
            raise ParseError(meta_data_property)
        earth_observation_meta_data = meta_data_property.find(eop + 'EarthObservationMetaData')
        if earth_observation_meta_data is None:
            raise ParseError(earth_observation_meta_data)
        eop_identifier = earth_observation_meta_data.findtext(eop + 'identifier')
        if eop_identifier is None:
            raise ParseError(eop_identifier)
        self.eop_identifier = eop_identifier
        doi = earth_observation_meta_data.find(eop + 'doi')
        if doi is None:
            raise ParseError(doi)
        self.doi = doi.text  # Digital Object Identifier
        self.acquisition_type = earth_observation_meta_data.findtext(eop + 'acquisitionType')
        self.acquisition_subtype = earth_observation_meta_data.findtext(eop + 'acquisitionSubType')
        type_code = earth_observation_meta_data.findtext(eop + 'productType', '')
        product_type_info = product_types.find_product(type_code)
        if product_type_info is not None:
            self._product_type_info = product_type_info
        self.product_status = earth_observation_meta_data.findtext(eop + 'status')

        # Mandatory for Raw data: Downlink information
        downlinked_to = earth_observation_meta_data.find(eop + 'downlinkedTo')
        if downlinked_to is not None:
            downlink_info = downlinked_to.find(eop + 'DownlinkInformation')
            if downlink_info is None:
                raise ParseError(downlink_info)
            self.acquisition_station = downlink_info.findtext(eop + 'acquisitionStation')
            self.acquisition_date = _time_from_iso(downlink_info.findtext(eop + 'acquisitionDate'))

        processing = earth_observation_meta_data.find(eop + 'processing')  # Data processing information
        if processing is None:
            raise ParseError(processing)
        processing_info = processing.find(eop + 'ProcessingInformation')
        if processing_info is None:
            raise ParseError(processing_info)
        self.processing_centre_code = processing_info.findtext(eop + 'processingCenter')
        # proc_center.set('codeSpace', 'urn:esa:eop:Biomass:facility')
        processing_date = _time_from_iso_short(processing_info.findtext(eop + 'processingDate'))
        if processing_date is None:
            raise ParseError(processing_date)
        self.processing_date = processing_date
        processor_name = processing_info.findtext(eop + 'processorName')
        if processor_name is None:
            raise ParseError(processor_name)
        self.processor_name = processor_name
        processor_version = processing_info.findtext(eop + 'processorVersion')
        if processor_version is None:
            raise ParseError(processor_version)
        self.processor_version = processor_version
        self._processing_level = processing_info.findtext(eop + 'processingLevel')

        self.auxiliary_ds_file_names.clear()
        for proc_info in processing_info.findall(eop + 'auxiliaryDataSetFileName'):
            if proc_info.text is not None:
                self.auxiliary_ds_file_names.append(proc_info.text)

        processing_mode = processing_info.find(eop + 'processingMode')
        if processing_mode is None:
            raise ParseError(processing_mode)
        self.processing_mode = processing_mode.text    # attrib={'codeSpace': 'urn:esa:eop:Biomass:class'}

        # Manadatory for raw/raws
        self.nr_transfer_frames = 0
        self.nr_transfer_frames_erroneous = 0
        self.nr_transfer_frames_corrupt = 0

        self.nr_instrument_source_packets = 0
        self.nr_instrument_source_packets_erroneous = 0
        self.nr_instrument_source_packets_corrupt = 0

        self.reference_documents.clear()
        for doc in earth_observation_meta_data.findall(eop + 'refDoc'):
            if doc.text is not None:
                self.reference_documents.append(doc.text)
