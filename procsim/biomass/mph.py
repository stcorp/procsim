'''
Copyright (C) 2021 S[&]T, The Netherlands.

Parse and generate Biomass Main Product Headers.
Ref: BIO-ESA-EOPG-EEGS-TN-0051
'''

import datetime
import common
from xml.etree import ElementTree as et

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

# TODO: do this more Pythonesque :)
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


class Acquisition:
    '''Data class, hold acquisition parameters for MPH'''
    def __init__(self):
        self.orbit_number: int = 1
        self.last_orbit_number: int = 1
        self.orbit_direction: str = 'ASCENDING'  # Or DECENDING
        self.track_nr: int = 133                 # gml:CodeWithAuthorityType
        self.slice_frame_nr = '___'              # or the actual slice/frame number
        self.anx_date = datetime.datetime.now()
        self.start_time: int = 0                 # in ms since ANX
        self.completion_time: int = 0            # in ms since ANX
        self.mission_phase: str = 'COMMISSIONING'    # Or INTERFEROMETRIC, TOMOGRAPHIC
        self.instrument_config_id: int = 1
        self.data_take_id: int = 0
        self.orbit_drift_flag: bool = False
        self.global_coverage_id: str = 'NA'      # 1..6 or DR, refer to PDGS Products Naming Convention document
        self.major_cycle_id: str = '1'           # 1..7, refer to PDGS Products Naming Convention document
        self.repeat_cycle_id: str = 'DR'         # 1..7 or DR, refer to PDGS Products Naming Convention document
        # self.observed_property: str = ''
        # self.feature_of_interest: str = ''

        self._polaristation_channels: str = 'HH, HV, VH, VV'  # FIXED
        self._polarisation_mode: str = 'Q'                    # FIXED
        self._antenna_direction: str = 'LEFT'                 # FIXED


class MainProductHeader:
    '''This class is responsible for parsing and creating the Biomass Main
    Product Header (MPH).'''
    def __init__(self):
        # TODO: From identifier?
        self._is_raw = True
        self._is_hktm = True
        self._is_pid_pc = True
        self._is_level0 = True
        self._is_level1 = True
        self._is_level2a = True
        self._is_aux = False

        self.satellite_name = 'Biomass'  # Fixed
        self.sensor_name = 'P-SAR'       # Fixed
        self.sensor_type = 'RADAR'       # Fixed
        self.browse_type = 'QUICKLOOK'   # Fixed

        self.eop_identifier = 'BIO_S2_SCS__1S_20230101T120000_20230101T120021_I_G03_M03_C03_T131_F155_01_ACZ976'
        self.begin_position = datetime.datetime(2021, 1, 1, 0, 0, 0)
        self.end_position = datetime.datetime.now()
        self.time_position = datetime.datetime.now()
        self.validity_start = datetime.datetime(2021, 1, 1, 0, 0, 0)
        self.validity_end = datetime.datetime.now()
        self.sensors = [{'type': self.sensor_type, 'mode': 'SM', 'swath_id': 'S2'}]  # Mode is SM, RO, EC, AC
        self.footprint_polygon = '-8.015716 -63.764648 -6.809171 -63.251038 -6.967323 -62.789612 -8.176149 -63.278503 -8.015716 -63.764648'
        self.center_points = '-7.492090 -63.27095'
        self.browse_ref_id = 'EPSG:4326'
        self.browse_image_filename = 'browse image filename'
        self.products = [
            {'file_name': 'product filename'},          # First product is mandatory and does not have the size/representation fields?!
            {'file_name': 'product filename', 'size': 100, 'representation': './schema/bio_l1_product.xsd'}
        ]
        self.product_baseline = 1

        self.doi = 'DOI'    # Digital Object Identifier
        self.acquisition_type = 'NOMINAL'   # OTHER, CALIBRATION or NOMINAL
        self.product_type = 'S1_RAW__0S'
        self.product_status = 'PLANNED'     # REJECTED, etc..

        self.processing_centre_code = 'ESR'
        self.processing_date = datetime.datetime.now()
        self.processor_name = 'L1 Processor'
        self.processor_version = '1.0'
        self.processing_level = 'Other: L1'
        self.auxiliary_ds_file_names = ['AUX_ORB_Filename', 'AUX_ATT_Filename']
        self.processing_mode = 'OPERATIONAL'
        self.biomass_source_product_ids = ['id']
        self.reference_documents = ['doc1', 'doc2']

        # Raw
        self.acquisition_station = 'SP'  # Spitzbergen, not sure
        self.downlink_date = datetime.datetime.now()

        # Raw HKTM info
        self.nr_transfer_frames = 0
        self.nr_transfer_frames_erroneous = 0
        self.nr_transfer_frames_corrupt = 0

        # Raw science/ancillary info
        self.nr_instrument_source_packets = 0
        self.nr_instrument_source_packets_erroneous = 0
        self.nr_instrument_source_packets_corrupt = 0

        # L0 and L1 info
        acquisition = Acquisition()
        self.acquisitions = [acquisition]
        self.tai_utc_diff = 0

        # L0 info
        self.nr_l0_lines = '387200,387200'  # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.nr_l0_lines_missing = '0,0'  # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.nr_l0_lines_corrupt = '0,0'  # 2 comma separated integers, being numOfLinesHPol,numOfLinesVPol
        self.incomplete_l0_slice = False
        self.partial_l0_slice = False
        self.l1_frames_in_l0 = '0,1,2,4,5'

        # L1 info
        self.incomplete_l1_frame = False
        self.partial_l1_frame = False

        for key, value in mph_namespaces.items():
            et.register_namespace(key, value)

    def _insert_time_period(self, parent, start, stop, id):
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
        mph = et.Element(bio + 'EarthObservation')
        mph.set(gml + 'id', self.eop_identifier + '_1')

        phenomenon_time = et.SubElement(mph, om + 'phenomenonTime')
        self._insert_time_period(phenomenon_time, self.begin_position, self.end_position, 2)

        result_time = et.SubElement(mph, om + 'resultTime')
        time_instant = et.SubElement(result_time, gml + 'TimeInstant')
        time_instant.set(gml + 'id', self.eop_identifier + '_3')
        time_position = et.SubElement(time_instant, gml + 'timePosition')
        time_position.text = _time_as_iso(self.time_position)

        valid_time = et.SubElement(mph, om + 'validTime')
        self._insert_time_period(valid_time, self.validity_start, self.validity_end, 4)

        procedure = et.SubElement(mph, om + 'procedure')  # Procedure used to sense the data
        earth_observation_equipment = et.SubElement(procedure, eop + 'EarthObservationEquipment')  # Equipment used to sense the data
        earth_observation_equipment.set(gml + 'id', self.eop_identifier + '_5')
        platform = et.SubElement(earth_observation_equipment, eop + 'platform')  # Platform description
        Platform = et.SubElement(platform, eop + 'Platform')  # Nested element for platform description
        short_name = et.SubElement(Platform, eop + 'shortName')
        short_name.text = self.satellite_name

        instrument = et.SubElement(earth_observation_equipment, eop + 'instrument')  # Instrument description
        Instrument = et.SubElement(instrument, eop + 'Instrument')  # Nested element for instrument description
        short_name = et.SubElement(Instrument, eop + 'shortName')
        short_name.text = self.sensor_name

        # Mandatory for L0, L1, L2A products
        if (self._is_level0 or self._is_level1 or self._is_level2a) and self.sensors:
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
                framenr.text = acq.slice_frame_nr
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
        if self._is_level1 or self._is_level2a:
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
            center_of = et.SubElement(feature_of_interest, eop + 'centerOf')  # Acquisition centre representation structure
            point = et.SubElement(center_of, gml + 'Point')
            point.set(gml + 'id', self.eop_identifier + '_9')
            pos = et.SubElement(point, gml + 'pos')  # Coordinates of the centre of the acquisition
            pos.text = self.center_points

        result = et.SubElement(mph, om + 'result')  # Observation result
        earth_observation_result = et.SubElement(result, eop + 'EarthObservationResult')
        earth_observation_result.set(gml + 'id', self.eop_identifier + '_10')

        # Mandatory for L1 products
        if self._is_level1:
            browse = et.SubElement(earth_observation_result, eop + 'browse')
            browse_info = et.SubElement(browse, eop + 'BrowseInformation')
            browse_type = et.SubElement(browse_info, eop + 'type').text = self.browse_type
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
                baseline = '{:02}'.format(self.product_baseline)
                et.SubElement(product_information, eop + 'version').text = baseline

        meta_data_property = et.SubElement(mph, eop + 'metaDataProperty')  # Observation metadata
        earth_observation_meta_data = et.SubElement(meta_data_property, bio + 'EarthObservationMetaData')
        et.SubElement(earth_observation_meta_data, eop + 'identifier').text = self.eop_identifier
        et.SubElement(earth_observation_meta_data, eop + 'doi').text = self.doi  # Digital Object Identifier'
        et.SubElement(earth_observation_meta_data, eop + 'acquisitionType').text = self.acquisition_type
        et.SubElement(earth_observation_meta_data, eop + 'productType').text = self.product_type
        et.SubElement(earth_observation_meta_data, eop + 'status').text = self.product_status

        # Mandatory for Raw data: Downlink information
        if self._is_raw:
            downlinked_to = et.SubElement(earth_observation_meta_data, eop + 'downlinkedTo')
            downlink_info = et.SubElement(downlinked_to, eop + 'DownlinkInformation')
            et.SubElement(downlink_info, eop + 'acquisitionStation').text = self.acquisition_station
            et.SubElement(downlink_info, eop + 'acquisitionDate').text = _time_as_iso(self.downlink_date)

        processing = et.SubElement(earth_observation_meta_data, eop + 'processing')  # Data processing information
        processing_info = et.SubElement(processing, bio + 'ProcessingInformation')
        proc_center = et.SubElement(processing_info, eop + 'processingCenter')
        proc_center.text = self.processing_centre_code
        proc_center.set('codeSpace', 'urn:esa:eop:Biomass:facility')
        et.SubElement(processing_info, eop + 'processingDate').text = _time_as_iso_short(self.processing_date)
        et.SubElement(processing_info, eop + 'processorName').text = self.processor_name
        et.SubElement(processing_info, eop + 'processorVersion').text = self.processor_version
        et.SubElement(processing_info, eop + 'processingLevel').text = self.processing_level

        if not self._is_aux:
            for name in self.auxiliary_ds_file_names:
                et.SubElement(processing_info, eop + 'auxiliaryDataSetFileName').text = name

        et.SubElement(processing_info, eop + 'processingMode', attrib={'codespace': 'urn:esa:eop:Biomass:class'}).text = self.processing_mode

        if self._is_level0 or self._is_level1 or self._is_level2a:
            for id in self.biomass_source_product_ids:
                et.SubElement(processing_info, bio + 'sourceProduct').text = id

        if self._is_level0 or self._is_level1:
            et.SubElement(earth_observation_meta_data, bio + 'TAI-UTC').text = str(self.tai_utc_diff)

        if self._is_raw:
            if self._is_hktm:
                et.SubElement(earth_observation_meta_data, bio + 'numOfTFs').text = str(self.nr_transfer_frames)
                et.SubElement(earth_observation_meta_data, bio + 'numOfTFsWithErrors').text = str(self.nr_transfer_frames_erroneous)
                et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedTFs').text = str(self.nr_transfer_frames_corrupt)
            if self._is_pid_pc:
                et.SubElement(earth_observation_meta_data, bio + 'numOfISPs').text = str(self.nr_instrument_source_packets)
                et.SubElement(earth_observation_meta_data, bio + 'numOfISPsWithErrors').text = str(self.nr_instrument_source_packets_erroneous)
                et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedISPs').text = str(self.nr_instrument_source_packets_corrupt)

        if self._is_level0:
            et.SubElement(earth_observation_meta_data, bio + 'numOfLines').text = self.nr_l0_lines
            et.SubElement(earth_observation_meta_data, bio + 'numOfMissingLines').text = self.nr_l0_lines_missing
            et.SubElement(earth_observation_meta_data, bio + 'numOfCorruptedLines').text = self.nr_l0_lines_corrupt
            et.SubElement(earth_observation_meta_data, bio + 'incompleteSlice').text = str(self.incomplete_l0_slice).lower()
            et.SubElement(earth_observation_meta_data, bio + 'partialSlice').text = str(self.partial_l0_slice).lower()
            et.SubElement(earth_observation_meta_data, bio + 'framesList').text = self.l1_frames_in_l0

        if self._is_level1:
            et.SubElement(earth_observation_meta_data, bio + 'incompleteFrame').text = str(self.incomplete_l1_frame).lower()
            et.SubElement(earth_observation_meta_data, bio + 'partialFrame').text = str(self.partial_l1_frame).lower()

        for doc in self.reference_documents:
            et.SubElement(earth_observation_meta_data, bio + 'refDoc').text = doc

        # Create XML
        tree = et.ElementTree(mph)
        common.indent_xml(tree.getroot())
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
        time_position = time_instant.find(gml + 'timePosition')
        self.time_position = _time_from_iso(time_position.text)

        valid_time = root.find(om + 'validTime')
        self.validity_start, self.validity_end = self._parse_time_period(valid_time, 4)

        procedure = root.find(om + 'procedure')  # Procedure used to sense the data
        earth_observation_equipment = procedure.find(eop + 'EarthObservationEquipment')  # Equipment used to sense the data
        # earth_observation_equipment.set(gml + 'id', self.eop_identifier + '_5')
        platform = earth_observation_equipment.find(eop + 'platform')  # Platform description
        Platform = platform.find(eop + 'Platform')  # Nested element for platform description
        short_name = Platform.find(eop + 'shortName')
        self.satellite_name = short_name.text

        instrument = earth_observation_equipment.find(eop + 'instrument')  # Instrument description
        Instrument = instrument.find(eop + 'Instrument')  # Nested element for instrument description
        short_name = Instrument.find(eop + 'shortName')
        self.sensor_name = short_name.text

        # Mandatory for L0, L1, L2A products
        if self._is_level0 or self._is_level1 or self._is_level2a:
            self.sensors = []
            # TODO: check if the 'sensor' element is mandatory, even if there are no sensors.
            sensor = earth_observation_equipment.find(eop + 'sensor')
            for Sensor in sensor.findall(eop + 'Sensor'):
                s = {}
                sensor_type = Sensor.find(eop + 'sensorType')
                s['type'] = sensor_type.text
                sensor_mode = Sensor.find(eop + 'operationalMode')
                # sensor_mode.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:operationalMode')
                s['mode'] = sensor_mode.text
                swath_id = Sensor.find(eop + 'swathIdentifier')
                # swath_id.set('codeSpace', 'urn:esa:eop:Biomass:PSAR:swathIdentifier')
                s['swath_id'] = swath_id.text
                self.sensors.append(s)

        # Mandatory for L0 and L1 products
        if self._is_level0 or self._is_level1:
            self.acquisitions = []
            acquisition_params = earth_observation_equipment.find(eop + 'acquisitionParameters')
            for acquisition in acquisition_params.findall(bio + 'Acquisition'):
                acq = Acquisition()
                acq.orbit_number = int(acquisition.find(eop + 'orbitNumber').text)
                acq.last_orbit_number = int(acquisition.find(eop + 'lastOrbitNumber').text)
                acq.orbit_direction = acquisition.find(eop + 'orbitDirection').text
                acq.track_nr = acquisition.find(eop + 'wrsLongitudeGrid').text
                # tracknr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:relativeOrbits')
                acq.slice_frame_nr = acquisition.find(eop + 'wrsLatitudeGrid').text
                # framenr.set(eop + 'codeSpace', 'urn:esa:eop:Biomass:frames')
                acq.anx_date = _time_from_iso(acquisition.find(eop + 'ascendingNodeDate').text)
                acq.start_time = int(acquisition.find(eop + 'startTimeFromAscendingNode').text)    # TODO ={'uom': 'ms'}
                acq.completion_time = int(acquisition.find(eop + 'completionTimeFromAscendingNode').text)  # TODO ={'uom': 'ms'}
                acq._polarisation_mode = acquisition.find(sar + 'polarisationMode').text
                acq._polaristation_channels = acquisition.find(sar + 'polarisationChannels').text
                acq._antenna_direction = acquisition.find(sar + 'antennaLookDirection').text
                acq.mission_phase = acquisition.find(bio + 'missionPhase').text
                acq.instrument_config_id = int(acquisition.find(bio + 'instrumentConfID').text)
                acq.data_take_id = int(acquisition.find(bio + 'dataTakeID').text)
                acq.orbit_drift_flag = acquisition.find(bio + 'orbitDriftFlag').text    # TODO: upper case?
                acq.global_coverage_id = acquisition.find(bio + 'globalCoverageID').text
                acq.major_cycle_id = acquisition.find(bio + 'majorCycleID').text
                acq.repeat_cycle_id = acquisition.find(bio + 'repeatCycleID').text
                self.acquisitions.append(acq)

        # observed_property = root.find(om + 'observedProperty')  # Observed property (Mandatory but empty)
        # observed_property.set(xsi + 'nil', 'true')
        # observed_property.set('nilReason', 'inapplicable')
        feature_of_interest = root.find(om + 'featureOfInterest')  # Observed area

        # Mandatory for L1, *L2A products
        if self._is_level1 or self._is_level2a:
            footprint = feature_of_interest.find(eop + 'Footprint')
            # footprint.set(gml + 'id', self.eop_identifier + '_6')
            multi_extent_of = footprint.find(eop + 'multiExtentOf')  # Footprint representation structure, coordinates in posList
            multi_surface = multi_extent_of.find(gml + 'MultiSurface')
            # multi_surface.set(gml + 'id', self.eop_identifier + '_7')
            surface_member = multi_surface.find(gml + 'surfaceMember')
            polygon = surface_member.find(gml + 'Polygon')
            # polygon.set(gml + 'id', self.eop_identifier + '_8')
            exterior = polygon.find(gml + 'exterior')
            linear_ring = exterior.find(gml + 'LinearRing')
            pos_list = linear_ring.find(gml + 'posList')  # Footprint points
            self.footprint_polygon = pos_list.text
            center_of = feature_of_interest.find(eop + 'centerOf')  # Acquisition centre representation structure
            point = center_of.find(gml + 'Point')
            # point.set(gml + 'id', self.eop_identifier + '_9')
            pos = point.find(gml + 'pos')  # Coordinates of the centre of the acquisition
            self.center_points = pos.text

        result = root.find(om + 'result')  # Observation result
        earth_observation_result = result.find(eop + 'EarthObservationResult')
        # earth_observation_result.set(gml + 'id', self.eop_identifier + '_10')

        # Mandatory for L1 products
        if self._is_level1:
            browse = earth_observation_result.find(eop + 'browse')
            browse_info = browse.find(eop + 'BrowseInformation')
            self.browse_type = browse_info.find(eop + 'type').text
            browse_ref_id = browse_info.find(eop + 'referenceSystemIdentifier')  # Coordinate reference system name
            self.browse_ref_id = browse_ref_id.text
            # browse_ref_id.set('codeSpace', 'urn:esa:eop:crs')
            # self._insert_file_name(browse_info, self.browse_image_filename)
            self.browse_image_filename = self._parse_file_name(browse_info)

        self.products = []
        for product in earth_observation_result.findall(eop + 'product'):
            product_information = product.find(bio + 'ProductInformation')
            file_name = self._parse_file_name(product_information)
            version = product_information.find(eop + 'version')
            if version is not None:
                self.product_baseline = int(version.text)
                self.products.append({'file_name': file_name})
            else:
                size = int(product_information.find(eop + 'size').text)  # attrib={'uom': 'bytes'}
                representation = product_information.find(bio + 'rds').text
                self.products.append({'file_name': file_name, 'size': size, 'representation': representation})

        meta_data_property = root.find(eop + 'metaDataProperty')  # Observation metadata
        earth_observation_meta_data = meta_data_property.find(bio + 'EarthObservationMetaData')
        self.eop_identifier = earth_observation_meta_data.find(eop + 'identifier').text
        self.doi = earth_observation_meta_data.find(eop + 'doi').text  # Digital Object Identifier'
        self.acquisition_type = earth_observation_meta_data.find(eop + 'acquisitionType').text
        self.product_type = earth_observation_meta_data.find(eop + 'productType').text
        self.product_status = earth_observation_meta_data.find(eop + 'status').text

        # Mandatory for Raw data: Downlink information
        if self._is_raw:
            downlinked_to = earth_observation_meta_data.find(eop + 'downlinkedTo')
            downlink_info = downlinked_to.find(eop + 'DownlinkInformation')
            self.acquisition_station = downlink_info.find(eop + 'acquisitionStation').text
            self.downlink_date = _time_from_iso(downlink_info.find(eop + 'acquisitionDate').text)

        processing = earth_observation_meta_data.find(eop + 'processing')  # Data processing information
        processing_info = processing.find(bio + 'ProcessingInformation')
        proc_center = processing_info.find(eop + 'processingCenter')
        self.processing_centre_code = proc_center.text
        # proc_center.set('codeSpace', 'urn:esa:eop:Biomass:facility')
        self.processing_date = _time_from_iso_short(processing_info.find(eop + 'processingDate').text)
        self.processor_name = processing_info.find(eop + 'processorName').text
        self.processor_version = processing_info.find(eop + 'processorVersion').text
        self.processing_level = processing_info.find(eop + 'processingLevel').text

        if not self._is_aux:
            self.auxiliary_ds_file_names = []
            for proc_info in processing_info.findall(eop + 'auxiliaryDataSetFileName'):
                self.auxiliary_ds_file_names.append(proc_info.text)

        self.processing_mode = processing_info.find(eop + 'processingMode').text    # attrib={'codespace': 'urn:esa:eop:Biomass:class'}

        if self._is_level0 or self._is_level1 or self._is_level2a:
            for source_product in processing_info.findall(bio + 'sourceProduct'):
                self.biomass_source_product_ids.append(source_product.text)

        if self._is_level0 or self._is_level1:
            self.tai_utc_diff = int(earth_observation_meta_data.find(bio + 'TAI-UTC').text)
        if self._is_raw:
            if self._is_hktm:
                self.nr_transfer_frames = int(earth_observation_meta_data.find(bio + 'numOfTFs').text)
                self.nr_transfer_frames_erroneous = int(earth_observation_meta_data.find(bio + 'numOfTFsWithErrors').text)
                self.nr_transfer_frames_corrupt = int(earth_observation_meta_data.find(bio + 'numOfCorruptedTFs').text)
            if self._is_pid_pc:
                self.nr_instrument_source_packets = int(earth_observation_meta_data.find(bio + 'numOfISPs').text)
                self.nr_instrument_source_packets_erroneous = int(earth_observation_meta_data.find(bio + 'numOfISPsWithErrors').text)
                self.nr_instrument_source_packets_corrupt = int(earth_observation_meta_data.find(bio + 'numOfCorruptedISPs').text)

        if self._is_level0:
            self.nr_l0_lines = earth_observation_meta_data.find(bio + 'numOfLines').text
            self.nr_l0_lines_missing = earth_observation_meta_data.find(bio + 'numOfMissingLines').text
            self.nr_l0_lines_corrupt = earth_observation_meta_data.find(bio + 'numOfCorruptedLines').text
            self.incomplete_l0_slice = earth_observation_meta_data.find(bio + 'incompleteSlice').text
            self.partial_l0_slice = earth_observation_meta_data.find(bio + 'partialSlice').text
            self.l1_frames_in_l0 = earth_observation_meta_data.find(bio + 'framesList').text

        if self._is_level1:
            self.incomplete_l1_frame = earth_observation_meta_data.find(bio + 'incompleteFrame').text
            self.partial_l1_frame = earth_observation_meta_data.find(bio + 'partialFrame').text

        for doc in earth_observation_meta_data.findall(bio + 'refDoc'):
            self.reference_documents.append(doc.text)
