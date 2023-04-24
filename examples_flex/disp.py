import os
import xml.etree.ElementTree as ET

import tabulate

props = ['dataTakeID', 'sensorDetector', 'slicingGridFrameNumber', 'sliceStartPosition', 'sliceStopPosition', 'completenessAssesment']
prefix = 'FLX_RWS'

eop = '{http://www.opengis.net/eop/2.1}'

lines = []
for f in os.listdir('workspace'):
    if f.startswith(prefix):
        tree = ET.parse(f'workspace/{f}/{f.lower()}.xml')
        attrs = {}
        for info in tree.findall(f'{eop}metaDataProperty/{eop}EarthObservationMetaData/{eop}vendorSpecific/{eop}SpecificInformation'):
            attrs[info.find(f'{eop}localAttribute').text] = info.find(f'{eop}localValue').text
        lines.append([f] + [attrs.get(prop, '_') for prop in props])

# sort on filename start, dataTakeID, sensor, frame nr
lines = sorted(lines, key=lambda x: (x[0][:10], x[1], x[2], x[3]))

print(tabulate.tabulate(lines, headers=['filename'] + props))
