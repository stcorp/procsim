import os
import re
import xml.etree.ElementTree as ET
import sys
import tabulate

props = ['dataTakeID', 'sensorDetector', 'slicingGridFrameNumber', 'sliceStartPosition',
         'sliceStopPosition', 'completenessAssesment', 'calibrationID']
prefix = 'FLX_'


def _path_to_lower(path: str) -> str:
    """
    Convert path to lowercase, but keep 't' in datetime strings
    uppercase, according to ESA-EOPG-EOEP-TN-0015 page 47.
    """
    return re.sub(pattern=r'(\d{8})t(\d{6})', repl=r'\1T\2', string=path.lower())


eop = '{http://www.opengis.net/eop/2.1}'
if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = 'workspace'

if len(sys.argv) > 2:
    filter_str = sys.argv[2]
else:
    filter_str = ''

lines = []

for f in os.listdir(path):
    if f.startswith(prefix) and filter_str in f:
        tree = ET.parse(f'{path}/{f}/{_path_to_lower(f)}.xml')
        attrs = {}
        for info in tree.findall(f'{eop}metaDataProperty/{eop}EarthObservationMetaData/{eop}vendorSpecific/{eop}SpecificInformation'):
            attrs[info.find(f'{eop}localAttribute').text] = info.find(f'{eop}localValue').text  # type: ignore
        lines.append([f] + [attrs.get(prop, '_') for prop in props])

# sort on filename start, dataTakeID, sensor, frame nr
lines = sorted(lines, key=lambda x: (x[0][:10], x[1], x[2], x[3]))

print(tabulate.tabulate(lines, headers=['filename'] + props))
