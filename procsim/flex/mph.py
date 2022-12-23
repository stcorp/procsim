
# TODO phenomenontime: RAW: downlink start/stop, AUX: validity
# TODO ref. orbit numbers?
# TODO product byte size 
# TODO NOMINAL -> CALIBRATION/OTHER?
# TODO aqcuisition subtype missing from example?

XML = '''<?xml version="1.0" encoding="utf-8"?>
<?xml-stylesheet type="text/xsl" href="../schematron/schematron_skeleton_for_eop.xsl.xsl"?>
<opt:EarthObservation xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ows="http://www.opengis.net/ows/2.0" xmlns:opt="http://www.opengis.net/opt/2.1" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:om="http://www.opengis.net/om/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:eop="http://www.opengis.net/eop/2.1" gml:id="{eop_id}_1" xsi:schemaLocation="http://www.opengis.net/opt/2.1 ./xsd/opt.xsd">
  <om:phenomenonTime>
    <gml:TimePeriod gml:id="{eop_id}_2">
      <gml:beginPosition>{acq_start}</gml:beginPosition>
      <gml:endPosition>{acq_end}</gml:endPosition>
    </gml:TimePeriod>
  </om:phenomenonTime>
  <om:resultTime>
    <gml:TimeInstant gml:id="{eop_id}_3">
      <gml:timePosition>{acq_end}</gml:timePosition>
    </gml:TimeInstant>
  </om:resultTime>
  <om:procedure>
    <eop:EarthObservationEquipment gml:id="{eop_id}_4">
      <eop:platform>
        <eop:Platform>
          <eop:shortName>FLEX</eop:shortName>
        </eop:Platform>
      </eop:platform>
      <eop:instrument>
        <eop:Instrument>
          <eop:shortName>FLORIS</eop:shortName>
        </eop:Instrument>
      </eop:instrument>
      <eop:sensor>
        <eop:Sensor>
          <eop:sensorType>OPTICAL</eop:sensorType>
          <eop:operationalMode codeSpace="urn:esa:eop:FLORIS:operationalMode">{operational_mode}</eop:operationalMode>
        </eop:Sensor>
      </eop:sensor>
      <eop:acquisitionParameters>
        <eop:Acquisition>
          <eop:orbitNumber>1</eop:orbitNumber>
          <eop:lastOrbitNumber>1</eop:lastOrbitNumber>
          <eop:orbitDirection>ASCENDING</eop:orbitDirection>
          <eop:illuminationAzimuthAngle uom="deg">10.2</eop:illuminationAzimuthAngle>
          <eop:acrossTrackIncidenceAngle uom="deg">-14.0</eop:acrossTrackIncidenceAngle>
          <eop:alongTrackIncidenceAngle uom="deg">-13.9</eop:alongTrackIncidenceAngle>
          <eop:pitch uom="deg">0</eop:pitch>
          <eop:roll uom="deg">0</eop:roll>
          <eop:yaw uom="deg">0</eop:yaw>
        </eop:Acquisition>
      </eop:acquisitionParameters>
    </eop:EarthObservationEquipment>
  </om:procedure>
  <om:observedProperty xsi:nil="true" nilReason="inapplicable"/>
  <om:featureOfInterest>
    <eop:Footprint gml:id="{eop_id}_5">
      <eop:multiExtentOf>
        <gml:MultiSurface gml:id="{eop_id}_6">
          <gml:surfaceMember>
            <gml:Polygon gml:id="{eop_id}_7">
              <gml:exterior>
                <gml:LinearRing>
                  <gml:posList>-8.015716 -63.764648 -6.809171 -63.251038 -6.967323 -62.789612 -8.176149 -63.278503 -8.015716 -63.764648</gml:posList>
                </gml:LinearRing>
              </gml:exterior>
            </gml:Polygon>
          </gml:surfaceMember>
        </gml:MultiSurface>
      </eop:multiExtentOf>
      <eop:centerOf>
        <gml:Point gml:id="{eop_id}_8">
          <gml:pos>-7.492090 -63.27095</gml:pos>
        </gml:Point>
      </eop:centerOf>
    </eop:Footprint>
  </om:featureOfInterest>
  <om:result>
    <eop:EarthObservationResult gml:id="{eop_id}_9">
      <eop:product>
        <eop:ProductInformation>
          <eop:fileName>
            <ows:ServiceReference xlink:href="{eop_id}">
              <ows:RequestMessage/>
            </ows:ServiceReference>
          </eop:fileName>
          <eop:version>{eop_version}</eop:version>
          <eop:timeliness>NOMINAL</eop:timeliness>
        </eop:ProductInformation>
      </eop:product>
{products}
    </eop:EarthObservationResult>
  </om:result>
  <eop:metaDataProperty>
    <eop:EarthObservationMetaData>
      <eop:identifier>{eop_id}</eop:identifier>
      <eop:creationDate>{creation_time}</eop:creationDate>
      <eop:doi>10.5270/FLX-xxxxxxx</eop:doi>
      <eop:acquisitionType>NOMINAL</eop:acquisitionType>
      <eop:productType>{file_category}_{semdesc}</eop:productType>
      <eop:status>ARCHIVED</eop:status>
      <eop:statusSubType>ON-LINE</eop:statusSubType>
      <eop:downlinkedTo>
        <eop:DownlinkInformation>
          <eop:acquisitionStation codeSpace="urn:esa:eop:FLEX:stationCode">KSE</eop:acquisitionStation>
          <eop:acquisitionDate>{acq_start}</eop:acquisitionDate>
        </eop:DownlinkInformation>
      </eop:downlinkedTo>
      <eop:archivedIn>
        <eop:ArchivingInformation>
          <eop:archivingCenter codeSpace="urn:esa:eop:FLEX:stationCode">ESR</eop:archivingCenter>
          <eop:archivingDate>{acq_end}</eop:archivingDate>
        </eop:ArchivingInformation>
      </eop:archivedIn>
      <eop:productQualityDegradation uom="%">25</eop:productQualityDegradation>
      <eop:productQualityDegradationQuotationMode>AUTOMATIC</eop:productQualityDegradationQuotationMode>
      <eop:productQualityStatus>DEGRADED</eop:productQualityStatus>
      <eop:productQualityDegradationTag codeSpace="urn:esa:eop:FLEX:qcDergadationTags">RADIOMETRIC</eop:productQualityDegradationTag>
      <eop:productQualityReportURL>http://xxx/xxx/xxx.pdf</eop:productQualityReportURL>
      <eop:processing>
        <eop:ProcessingInformation>
          <eop:processingCenter codeSpace="urn:esa:eop:FLEX:facility">ESR</eop:processingCenter>
          <eop:processingDate>{acq_end}</eop:processingDate>
          <eop:processorName>{processor_name}</eop:processorName>
          <eop:processorVersion>01.10</eop:processorVersion>
          <eop:processingLevel>other: {processing_level}</eop:processingLevel>
          <eop:nativeProductFormat>dat</eop:nativeProductFormat>
          <eop:auxiliaryDataSetFileName>AUX_CCDB_FP_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_CCDB_TEM_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_SCNVAL_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_EOCFI_ORBSVs_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_EOCFI_ORBSCT_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_EOCFI_ATTREF_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_EOCFI_ATTDEF_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_EOCFI_DEMCFG_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_EOCFI_IERSBU_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_LandSeaMap_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_GCP_FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_ECWMF_FOR__FileName</eop:auxiliaryDataSetFileName>
          <eop:auxiliaryDataSetFileName>AUX_ECWMF_ANA__FileName</eop:auxiliaryDataSetFileName>
          <eop:processingMode>NOMINAL</eop:processingMode>
        </eop:ProcessingInformation>
      </eop:processing>
{meta}
    </eop:EarthObservationMetaData>
  </eop:metaDataProperty>
</opt:EarthObservation>
'''

XML_PRODUCT = '''\
      <eop:product>
        <eop:ProductInformation>
          <eop:fileName>
            <ows:ServiceReference xlink:href="./{eop_id}{product_suffix}">
              <ows:RequestMessage/>
            </ows:ServiceReference>
          </eop:fileName>
          <eop:size uom="bytes">0</eop:size>
        </eop:ProductInformation>
      </eop:product>
'''

XML_VENDOR_SPECIFIC = '''\
      <eop:vendorSpecific>
        <eop:SpecificInformation>
          <eop:localAttribute>{attr_name}</eop:localAttribute>
          <eop:localValue>{attr_value}</eop:localValue>
        </eop:SpecificInformation>
      </eop:vendorSpecific>
'''

FMT1 = '%Y-%m-%dT%H:%M:%S.000Z' # TODO ms important?


def create(eop_id, operational_mode, acq_start, acq_end, creation_time, eop_version, file_category, semdesc, duration, cycle, rel_orbit, anx_elapsed):

    acq_start = acq_start.strftime(FMT1)
    acq_end = acq_end.strftime(FMT1)

    # L0/RAW specific
    products = ''
    if file_category == 'L0_':
        for suffix in ('lres', 'hre1', 'hre2'):
            product_suffix = f'_{suffix}.dat'
            products += XML_PRODUCT.format(**locals())

        processor_name = 'L0PF'
        processing_level = 'L0'
    else:
        product_suffix = '.dat'
        products += XML_PRODUCT.format(**locals())

        processor_name = 'AF'
        processing_level = 'RAW'  # TODO difference with RAWS?

    products = products.rstrip()

    meta = ''
    for attr_name, attr_value in [
        ('missionPhase', 'COMMISSIONING'),
        ('Ref_Doc', ''),  # TODO
        ('Task_Table_Name', ''),  # TODO
        ('Task_Table_Version', ''),  # TODO
        ('Duration', duration),
        ('Cycle_Number', cycle),
        ('Relative_Orbit_Number', rel_orbit),
        ('ANX_elapsed_time', anx_elapsed),
        ('ANX_elapsed_time', anx_elapsed),
        ('numOfISPs', 0),  # TODO
        ('numOfISPsWithErrors', 0),  # TODO
        ('numOfCorruptedISPs', 0),  # TODO
        ('numOfTFs', 0),  # TODO
        ('numOfTFsWithErrors', 0),  # TODO
        ('numOfCorruptedTFs', 0),  # TODO
    ]:
        meta += XML_VENDOR_SPECIFIC.format(**locals())
    meta = meta.rstrip()

    return XML.format(**locals())
