'''
Copyright (C) 2021 S[&]T, The Netherlands.

Biomass raw data generator.
'''
import datetime
import os
import sys

from lxml import etree as et

'''
This class is responsible for creating the correct directory/file names,
according to TODO.
'''
class ProductNameGenerator:
    def __init__(self):
        self.satellite_id = 'BIO'
        self.file_type = 'RAW_025_10'
        self.start_time = datetime.datetime(2021, 1, 1, 0, 0, 0)
        self.stop_time = datetime.datetime(2021, 1, 1, 1, 30, 0)
        self.downlink_time = datetime.datetime(2021, 1, 1, 2, 0, 0)
        self.baseline_identifier = 1
        self.compact_create_date = 'ACZ976'

    def _generate_prefix(self):
        name = '{}_{}_{}_{}_'\
            .format(self.satellite_id, self.file_type, 
            self.start_time.strftime('%Y%m%dT%H%M%S'),
            self.stop_time.strftime('%Y%m%dT%H%M%S'))            
        return name

    def generate_l0l1(self):
        return self._generate_prefix() + '<P>_G<CC>_M<NN>_C<nn>_T<TTT>_F<FFF>_<BB>_<DDDDDD>'

    def generate_path(self):
        name = self._generate_prefix() + 'D{}_{:02}_{}'\
            .format(
                self.downlink_time.strftime('%Y%m%dT%H%M%S'),
                self.baseline_identifier,
                self.compact_create_date
            )
        return name

    def generate_mph_file_name(self):
        return self.generate_path().lower() + '.xml'

    def generate_binary_file_name(self):
        name = self._generate_prefix() + 'D{}.dat'.format(
            self.downlink_time.strftime('%Y%m%dT%H%M%S')
        )
        return name.lower()

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


class MainProductHeader:
    '''This class is responsible for parsing and creating MPH files, according
    to TODO'''
    def __init__(self):
        self.eop_identifier = 'BIO_S2_SCS__1S_20230101T120000_20230101T120021_I_G03_M03_C03_T131_F155_01_ACZ976'
        self.sensors = ['Synthetic aperature radar']
        self.acquisitions= ['test']
        self.product_baseline = 'product_baseline'
        self.products = ['level0', 'level1']

    def generate(self, file_name):
        bio = "{%s}" % mph_namespaces['bio']
        gml = "{%s}" % mph_namespaces['gml']
        om = "{%s}" % mph_namespaces['om']
        eop = "{%s}" % mph_namespaces['eop']
        sar = "{%s}" % mph_namespaces['sar']
        ows = "{%s}" % mph_namespaces['ows']

        mph = et.Element(bio + 'EarthObservation', nsmap=mph_namespaces)
        mph.set(gml + 'id', self.eop_identifier + '_1')

        phenomenon_time = et.SubElement(mph, om + 'phenomenonTime')
        time_period = et.SubElement(phenomenon_time, gml + 'TimePeriod')
        time_period.set(gml + 'id', self.eop_identifier + '_2')
        begin_position = et.SubElement(time_period, gml + 'beginPosition')
        begin_position.text = 'todo'
        end_position = et.SubElement(time_period, gml + 'endPosition')
        end_position.text = 'todo'

        result_time = et.SubElement(mph, om + 'resultTime')        
        time_instant = et.SubElement(result_time, gml + 'TimeInstant')
        time_instant.set(gml + 'id', self.eop_identifier + '_3')
        time_position = et.SubElement(time_instant, gml + 'timePosition')
        time_position.text = 'todo'

        valid_time = et.SubElement(mph, om + 'validTime')
        time_period = et.SubElement(valid_time, gml + 'TimePeriod')
        time_period.set(gml + 'id', self.eop_identifier + '_4')
        begin_position = et.SubElement(time_period, gml + 'beginPosition')
        begin_position.text = 'todo'
        end_position = et.SubElement(time_period, gml + 'endPosition')
        end_position.text = 'todo'

        procedure = et.SubElement(mph, om + 'procedure')    # Procedure used to sense the data
        earth_observation_equipment = et.SubElement(procedure, eop + 'EarthObservationEquipment') # Equipment used to sense the data
        platform = et.SubElement(earth_observation_equipment, eop + 'platform') # Platform description
        Platform = et.SubElement(platform, eop + 'Platform') # Nested element for platform description
        short_name = et.SubElement(Platform, eop + 'shortName') # Satellite name
        short_name.text = 'Satellite name'

        instrument = et.SubElement(earth_observation_equipment, eop + 'instrument') # Instrument description
        Instrument = et.SubElement(instrument, eop + 'Instrument') # Nested element for instrument description
        short_name = et.SubElement(Instrument, eop + 'shortName') # Sensor name
        short_name.text = 'Sensor name'

        if self.sensors:
            sensor = et.SubElement(earth_observation_equipment, eop + 'sensor') # Sensor description
            Sensor = et.SubElement(sensor, eop + 'Sensor') #  Nested element for sensor description
            for s in self.sensors:
                sensor_type = et.SubElement(Sensor, eop + 'sensorType')
                sensor_type.text = 'Sensor type' 
                sensor_mode = et.SubElement(Sensor, eop + 'operationalMode')
                sensor_mode.text = 'Sensor mode'
                swath_id = et.SubElement(Sensor, eop + 'swathIdentifier')
                swath_id.text = 'Swath id'
        
        if self.acquisitions:
            acquisition_params = et.SubElement(earth_observation_equipment, eop + 'acquisitionParameters')
            acquisition = et.SubElement(acquisition_params, bio + 'Acquisition')
            for ap in self.acquisitions:
                et.SubElement(acquisition, eop + 'orbitNumber').text = 'orbit number (orbit start)'
                et.SubElement(acquisition, eop + 'lastOrbitNumber').text = 'Last orbit number (orbit stop)'
                et.SubElement(acquisition, eop + 'orbitDirection').text = 'Orbit direction'
                et.SubElement(acquisition, eop + 'wrsLongitudeGrid').text = 'Track number'
                et.SubElement(acquisition, eop + 'wrsLatitudeGrid').text = 'Frame number'
                et.SubElement(acquisition, eop + 'ascendingNodeDate').text = 'Date and time of ANX'
                et.SubElement(acquisition, eop + 'startTimeFromAscendingNode').text = 'Start time from ANX'
                et.SubElement(acquisition, eop + 'completionTimeFromAscendingNode').text = 'Stop time from ANX'
                et.SubElement(acquisition, sar + 'polarisationMode').text = 'SAR Polarisation mode'
                et.SubElement(acquisition, sar + 'polarisationChannels').text = 'SAR Polarisation channels'
                et.SubElement(acquisition, sar + 'antennaLookDirection').text = 'SAR antenna look direction'
                et.SubElement(acquisition, bio + 'missionPhase').text = 'BIOMASS mission phase'
                et.SubElement(acquisition, bio + 'instrumentConfID').text = 'BIOMASS instrument configuration identifier'
                et.SubElement(acquisition, bio + 'dataTakeID').text = 'BIOMASS data take identifier'
                et.SubElement(acquisition, bio + 'orbitDriftFlag').text = 'BIOMASS orbit drift flag'
                et.SubElement(acquisition, bio + 'globalCoverageID').text = 'BIOMASS global coverage identifier'
                et.SubElement(acquisition, bio + 'majorCycleID').text = 'BIOMASS major cycle identifier'
                et.SubElement(acquisition, bio + 'repeatCycleID').text = 'BIOMASS repeat cycle identifier'

        et.SubElement(mph, om + 'observedProperty') # Observed property (empty)
        feature_of_interest = et.SubElement(mph, om + 'featureOfInterest') # Observed area
        ''' Optional : 
        eop:Footprint Footprint description
            eop:multiExtentOf Footprint representation structure, coordinates in posList
                gml:MultiSurface
                    gml:surfaceMember
                        gml:Polygon
                            gml:exterior
                                gml:LinearRing
                                    gml:posList Footprint points
        eop:centerOf Acquisition centre representation structure
            gml:Point
                gml:pos Coordinates of the centre of the acquisition
        '''
        result = et.SubElement(mph, om + 'result') # Observation result
        earth_observation_result = et.SubElement(result, eop + 'EarthObservationResult')
        ''' Optional :
        eop:browse
            eop:BrowseInformation
                eop:type Browse type
                eop:referenceSystemIdentifier Coordinate reference system name
                eop:fileName
                    ows:ServiceReference Browse Image filename
                        ows:RequestMessage download request (empty)
        '''
        product = et.SubElement(earth_observation_result, eop + 'product')
        product_information = et.SubElement(product, bio + 'ProductInformation')
        filename = et.SubElement(product_information, eop + 'fileName')
        service_reference = et.SubElement(filename, ows + 'ServiceReference')
        service_reference.text = 'Product filename'
        et.SubElement(service_reference, ows + 'RequestMessage') # download request (empty)

        et.SubElement(earth_observation_result, eop + 'version').text = self.product_baseline

        for prod in self.products:
            product = et.SubElement(earth_observation_result, eop + 'product')
            product_information = et.SubElement(product, bio + 'ProductInformation')
            filename = et.SubElement(product_information, eop + 'fileName')
            service_reference = et.SubElement(filename, ows + 'ServiceReference')
            service_reference.text = 'Product filename (internal files)'
            et.SubElement(service_reference, ows + 'RequestMessage') # download request (empty)
            et.SubElement(product_information, eop + 'size').text = 'Product size (Bytes?)'
            et.SubElement(product_information, bio + 'rds').text = 'Representation data file related to xml product'

        # Create XML
        tree = et.ElementTree(mph)
        tree.write(file_name, xml_declaration=True, pretty_print=True)


class RawProductGenerator:
    def __init__(self, output_path):
        self.output_path = output_path

    def _generate_bin_file(self, file_name):
        file = open(file_name, 'w')
        file.write('test')

    def generate(self, start_time, end_time):
        '''Generate raw data file(s) over the specified period.'''
        name_gen = ProductNameGenerator()
        self.eop_identifier = name_gen.generate_path()
        dir_name = os.path.join(self.output_path, self.eop_identifier)
        
        # Create directory
        print('Create {}'.format(dir_name))
        os.makedirs(dir_name, exist_ok=True)

        # Create MPH file
        file_name = os.path.join(dir_name, name_gen.generate_mph_file_name())
        mph = MainProductHeader()
        mph.generate(file_name)

        # Create binary telemetry file
        file_name = os.path.join(dir_name, name_gen.generate_binary_file_name())
        self._generate_bin_file(file_name)


def main():
    args = sys.argv[1:]
    output_path = 'data'
    if len(args) > 0:
        output_path = args[0]

    gen = RawProductGenerator(output_path)
    gen.generate(None, None)


if __name__ == "__main__":
    main()

