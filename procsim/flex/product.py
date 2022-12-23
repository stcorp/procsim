from datetime import datetime
import zipfile

import mph

FMT1 = '%Y%m%dT%H%M%S'


def main():
    mission_id = 'FLX'
    product_types = [
        ('EO',  'RWS', 'XS_OBS'),
        ('EO',  'RWS', 'XSPOBS'),
        ('EO',  'L0_', 'OBS___'),

        ('CAL', 'RWS', 'XS_CAL'),
        ('CAL', 'RWS', 'XSPCAL'),
        ('CAL', 'L0_', 'DARKNP'),
        ('CAL', 'L0_', 'DARKSR'),
        ('CAL', 'L0_', 'DARKSS'),
        ('CAL', 'L0_', 'DEFDAR'),
        ('CAL', 'L0_', 'DARKOC'),
        ('CAL', 'L0_', 'DRKMTF'),
        ('CAL', 'L0_', 'DRKSTR'),
        ('CAL', 'L0_', 'SPECSD'),
        ('CAL', 'L0_', 'SUN___'),
        ('CAL', 'L0_', 'DEFSUN'),
        ('CAL', 'L0_', 'MOON__'),
        ('CAL', 'L0_', 'MOONSL'),
        ('CAL', 'L0_', 'LINDES'),
        ('CAL', 'L0_', 'LINSEA'),
        ('CAL', 'L0_', 'LINSUN'),
        ('CAL', 'L0_', 'LINDAR'),
        ('CAL', 'L0_', 'CTE___'),
        ('CAL', 'L0_', 'SCNVAL'),
        ('CAL', 'L0_', 'COREG_'),
        ('CAL', 'L0_', 'SPECEO'),
        ('CAL', 'L0_', 'CLOUD_'),

        ('ANC', 'RWS', 'XS_ANC'),
        ('ANC', 'RWS', 'XSPANC'),
        ('ANC', 'RWS', 'SAT_TM'),
        ('ANC', 'RWS', 'NAVATT'),
        ('ANC', 'RWS', 'PDHUTM'),
        ('ANC', 'RWS', 'ICUDTM'),
        ('ANC', 'RWS', 'VAU_TM'),
        ('ANC', 'RWS', 'INSTTM'),
    ]

    sensing_start = datetime(2001,1,1,0)
    sensing_start_str = sensing_start.strftime(FMT1)
    sensing_stop = datetime(2001,1,1,1)
    sensing_stop_str = sensing_stop.strftime(FMT1)
    duration = '0128' # TODO integer, zfill?
    cycle = '011'
    rel_orbit = '045'
    anx_elapsed = '2826'
    baseline = 'ABCD'

    for data_type, file_category, semdesc in product_types:
        creation_time = datetime.now()
        creation_time_str = creation_time.strftime(FMT1)

        eop_id = f'FLX_{file_category}_{semdesc}_{sensing_start_str}_{sensing_stop_str}_{creation_time_str}_{duration}_{cycle}_{rel_orbit}_{anx_elapsed}_{baseline}'
        print(eop_id)

        mph_data = mph.create(eop_id, data_type, sensing_start, sensing_stop, creation_time, baseline, file_category, semdesc, int(duration), int(cycle), int(rel_orbit), int(anx_elapsed))

        with zipfile.ZipFile(f'{eop_id}.ZIP', 'w') as z:
            z.writestr(f'{eop_id}/{eop_id}.xml'.lower(), mph_data)

            if file_category == 'L0_':
                z.writestr(f'{eop_id}/{eop_id}_lres.dat'.lower(), b'')
                z.writestr(f'{eop_id}/{eop_id}_hre1.dat'.lower(), b'')
                z.writestr(f'{eop_id}/{eop_id}_hre2.dat'.lower(), b'')

            elif file_category == 'RWS':
                z.writestr(f'{eop_id}/{eop_id}.dat'.lower(), b'')

if __name__ == '__main__':
    main()
