#!/usr/bin/env python3
import os
import sys
import re
import xml.etree.ElementTree as ET
import subprocess
import shutil  # Import the shutil module

import logging
from logging.handlers import RotatingFileHandler


SERVER_IP = 'localhost'
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
EVENT_ID = sys.argv[2]

# გაშვებული სკრიპტის მისამართი
TEMP_DIR_PATH = SCRIPT_PATH + "/temp"
if not os.path.isdir(TEMP_DIR_PATH):
    os.mkdir(TEMP_DIR_PATH)

LOGS_DIR_PATH = SCRIPT_PATH + "/logs"
if not os.path.isdir(LOGS_DIR_PATH):
    os.mkdir(LOGS_DIR_PATH)

XML_PATH = TEMP_DIR_PATH + "/eq_log.xml"
HTML_FILE_PATH = TEMP_DIR_PATH + "/redirectPostEq.html"

# 4 ასევე მანძილის გრადუსებიდან კილომეტრებში გადასაყვანად ვიყენებთ 111.19492664455873 გამრავლებას რამდენად სწორია ?? 
KILOMETER_DEVIDED_DEGREE_RATIO = 111.19492664455873

SOFTWARE_NAMES = {'LOCSAT':'LocSAT(Seiscomp)'}
WAVE_TYPES = {'P':'Px'}

MAGNITUDE_TYPES = {'MLv':'mlv', 'MLh':'mlh', 'mb':'mb', 'ML':'ml', 'M':'M' }

FORM_LIST = []
STATIONS = {}

# Set up logging for the scheduler
LOG_FILENAME = f'{LOGS_DIR_PATH}/import_eq2.log'
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3  # Keep 3 backup log files

# Create a rotating file handler
rotating_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
rotating_handler.setFormatter(formatter)

# Set up the root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(rotating_handler)


def xml_dump(xml_path, event_id, server_ip):
    # seiscomp exec scxmldump -APMfmp -o /home/sysop/Code/Seiscomp_Scripts/import_eq2iesdata/temp/eq_log.xml -E grg2025fary -d localhost
    command = f'seiscomp exec scxmldump -APMfmp -o {xml_path} -E {event_id} -d {server_ip}'
    try:
        subprocess.run(command, check=True, shell=True )
    except subprocess.CalledProcessError as e:
        print("Error:", e)
        sys.exit(1)

# ეს ფუნქცია სეისკომპიდან მიღებულ დროს გადაიყვანს SHM-ის დროის ფორმატში
# მაგ: "2017-12-17T23:26:41.96Z" გადავა შემდეგი სახით : '17-DEC-2017_23:26:41.960'
def convert_seiscomp_time_to_shm_time(time):
	
	months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
	seiscomp_msec = time[20:23]
	seiscomp_msec_splited = seiscomp_msec.split('Z')
	a = seiscomp_msec_splited[0]	
	year = time[:4]
	day = time[8:10]
	month = time[5:7]
	HH = time[11:13]
	MM = time[14:16]
	ss = time[17:19]
	msec = a.ljust(3,'0')
	return day + "-" + months[int(month)-1] + "-" + year + "_"  + HH + ':' + MM + ':' + ss + '.' + msec

def convert_magnitude_name(magnitude):
    magnitude_name_lowercase = magnitude.lower()
    for key, value in MAGNITUDE_TYPES.items():
        if key.lower() == magnitude_name_lowercase:
            return value

    print(f'ERROR: This Magnitude Type: {magnitude} does not exist in iesdata.iliauni.edu.ge')
    logging.critical(f'{magnitude}, მაგნიტუდის ტიპი {magnitude} არ არსებობს iesdata.iliauni.edu.ge-ზე')
    return None

# ფუნქცია აგენერირებს input-ებს მიწოდებული name(სახელი) და value(მნიშვნელობა) მნიშვნელობებით
def generate_input(name, value, func_name='generate_input'):
    FORM_LIST.append("<input name='" + str(name) + "' type='text' value='" + str(value) + "' />")
    logging.debug(f'<{func_name} - name: {name}; value: {value}>')

# ფუნქცია აგენერირებს input-ებს
def smart_generate_input(name, element,first_child, second_child, round_number = None, convert_time_format = False):
	
    if element.find(first_child) is not None and element.find(first_child).find(second_child) is not None:
        value = element.find(first_child).find(second_child).text
        if round_number is not None:
            value = round(float(value), round_number)
        if convert_time_format:
            value = convert_seiscomp_time_to_shm_time(value)

        generate_input(name, value, func_name='smart_generate_input')

# ვავსებთ station ლექსიკონს იმ მიზნით რომ პიკები დაჯგუფდეს სადგურების მიხედვით
def picked_stations():
    # სადგურების წაკითხვა და input-ების გენერაცია
    arrivals = origin_element.findall('arrival')

    for arrival in arrivals:
        timeUsed = arrival.find('timeUsed').text
        if timeUsed == 'true':
            pick_id = arrival.find('pickID').text
            
            if pick_id.startswith('Pick'):
                manual_picked = True
                pick_element = eventParameters_element.find(f"*[@publicID='{pick_id}']")
                #სადგურის კოდი
            else:
                manual_picked = False
                pick_element = eventParameters_element.find(f".//amplitude[pickID='{pick_id}']")

            if pick_element is None:
                logging.warning(f'<picked_stations - pick_id: {pick_id} არ არის მონაცემი>')
                continue

            station_code = pick_element.find('waveformID').attrib['stationCode']

            if station_code not in STATIONS:
                STATIONS[station_code] = {}

            STATIONS[station_code]['network'] = pick_element.find('waveformID').attrib['networkCode']
            STATIONS[station_code]['channel'] = pick_element.find('waveformID').attrib['channelCode']

            if 'arrivals' not in STATIONS[station_code]:
                STATIONS[station_code]['arrivals'] = {}

            #წავიკითხოთ ტალღის სახელი
            phase = arrival.find('phase').text

            for key, value in WAVE_TYPES.items():
                if key.lower() == phase.lower():
                    phase = value
                    
            STATIONS[station_code]['azimuth'] = round(float(arrival.find('azimuth').text), 3)
            #+სადგურებიდან მანძილი გადადის გრადუსიდან კილომეტრში და ისე ხდება მნიშვნელობის შენახვა
            STATIONS[station_code]['distance'] = round(float(arrival.find('distance').text) * KILOMETER_DEVIDED_DEGREE_RATIO, 3)
            STATIONS[station_code]['arrivals'][phase] = {}

            #გასარკვევია როგორ გადავა iesdata-ზე 
            if arrival.find('timeResidual') is not None:
                STATIONS[station_code]['arrivals'][phase]['timeResidual'] = arrival.find('timeResidual').text
                if manual_picked:
                    STATIONS[station_code]['arrivals'][phase]['time'] = convert_seiscomp_time_to_shm_time(pick_element.find('time').find('value').text)
                else:
                    STATIONS[station_code]['arrivals'][phase]['time'] = ''
            if arrival.find('weight') is not None :
                STATIONS[station_code]['arrivals'][phase]['weight'] = arrival.find('weight').text
                if int(arrival.find('weight').text) > 0 :
                    STATIONS[station_code]['arrivals'][phase]['used_for_calculation'] = "Yes"
                else:
                    STATIONS[station_code]['arrivals'][phase]['used_for_calculation'] = "No"

        else:
            continue

#station ლექსიკონში მაგნიტუდების შევსება
def calculated_magnitudes():
    magnitude_elements = origin_element.findall('magnitude')
    for magnitude_element in magnitude_elements:
        stationMagnitudeContributions = magnitude_element.findall('stationMagnitudeContribution')

        for stationMagnitudeContribution in stationMagnitudeContributions:
            stationMagnitudeID = stationMagnitudeContribution.find('stationMagnitudeID').text
            stations_magnitude = origin_element.find("*[@publicID='" + stationMagnitudeID + "']")
            stations_amplitude_ID = stations_magnitude.find('amplitudeID').text
            station_amplitude = eventParameters_element.find("*[@publicID='" + stations_amplitude_ID + "']")
            # station_amplitude_value = station_amplitude.find('amplitude').find('value').text

            station_code = stations_magnitude.find('waveformID').attrib['stationCode']
            # print(station_code)
            # print(station_amplitude_value)
            #წავიკითხოთ მაგნიტუდის ტიპი და stations ლექსიკონში დავამატოთ შესაბამისი ახალი ლექსიკონი
            magnitude_type = convert_magnitude_name(stations_magnitude.find('type').text)
            if 'magnitudes' not in STATIONS[station_code]:
                STATIONS[station_code]['magnitudes'] = {}
            if 	magnitude_type not in STATIONS[station_code]['magnitudes']:
                STATIONS[station_code]['magnitudes'][magnitude_type] = {}
            # print(magnitude_type)
            # print(magnitude.find('magnitude').find('value').text)
            STATIONS[station_code]['magnitudes'][magnitude_type]['value'] = round(float(stations_magnitude.find('magnitude').find('value').text), 2)
            #+ თუ სადგურის მაგნიტუდების residual-ები არის მაშინ შეივსოს ლექსიკონი შესაბამისი ინფორმაციით
            if stationMagnitudeContribution.find('residual') is not None:
                STATIONS[station_code]['magnitudes'][magnitude_type]['residual'] = stationMagnitudeContribution.find('residual').text
            STATIONS[station_code]['magnitudes'][magnitude_type]['amplitude'] = station_amplitude.find('amplitude').find('value').text

if __name__ == '__main__':
    """
        გვჭირდება სკრიპტის სამი ნაწილი
        1) XML ფაილის დაგენერირება სეისკომპიდან.
        2) XML ფაილის სწორად გაპარსვა და საჭირო ინფორმაციის ამოღება
        3) XML ფაილიდან ამოღებული ინფორმაციის გადაცემა PHP ფაილისთვის
    """
    # 1) XML ფაილის დაგენერირება სეისკომპიდან scxmldump-ის გამოყენებით .
    xml_dump(XML_PATH, EVENT_ID, SERVER_IP)
    file = open(XML_PATH, "r")

    xml_file_content = re.sub(' xmlns="[^"]+"', '', file.read(), count=1)

    #String დან xml-ის "გაპარსვა"
    root = ET.fromstring(xml_file_content)
    #xml - ში origin ტეგის წაკითხვა
    eventParameters_element =  root.find('EventParameters')
    origin_element = eventParameters_element.find('origin')

    # მიწისძვრის პარამეტრების წაკითხვა და input-ების დაგენერირება
    #ამ ეტაპზე მოწმდება მიწისძვრა დათვლილია თუ არა რაიმე მეთოდით (მაგ:LOCSAT)
    if origin_element.find('methodID') is not None:
        soft = origin_element.find('methodID').text
        for key, value in SOFTWARE_NAMES.items():
            if key == soft:
                soft = value
                break
    else:
        soft = 'Raw'

    logging.debug(f'soft variable - {soft}')

    generate_input("soft", soft )

    smart_generate_input("EQ_time", origin_element, 'time', 'value', convert_time_format = True)
    smart_generate_input("EQ_rms", origin_element, 'time', 'uncertainty', 3)
    # generate_input("EQ_rms", round(float(origin_element.find('time').find('uncertainty').text), 3 ))

    smart_generate_input("EQ_latitude", origin_element, 'latitude', 'value', 4)
    smart_generate_input("EQ_err_lat", origin_element, 'latitude', 'uncertainty', 3)
    # generate_input("EQ_latitude", round(float(origin_element.find('latitude').find('value').text), 4 ))
    # generate_input("EQ_err_lat", round(float(origin_element.find('latitude').find('uncertainty').text), 3))

    smart_generate_input("EQ_longitude", origin_element, 'longitude', 'value', 4)
    smart_generate_input("EQ_err_long", origin_element, 'longitude', 'uncertainty', 3)
    # generate_input("EQ_longitude", round(float(origin_element.find('longitude').find('value').text), 4 ))
    # generate_input("EQ_err_long", round(float(origin_element.find('longitude').find('uncertainty').text), 3 ))

    smart_generate_input("EQ_depth", origin_element, 'depth', 'value', 3)
    smart_generate_input("EQ_err_depth", origin_element, 'depth', 'uncertainty', 3)
    # generate_input("EQ_depth", round(float(origin_element.find('depth').find('value').text), 3 ))
    # generate_input("EQ_err_depth", round(float(origin_element.find('depth').find('uncertainty').text), 3))

    smart_generate_input("EQ_phases_count", origin_element, 'quality', 'associatedPhaseCount', 3)
    smart_generate_input("EQ_phases_used_count", origin_element, 'quality', 'usedPhaseCount', 3)
    # generate_input("EQ_phases_count", origin_element.find('quality').find('associatedPhaseCount').text)
    # generate_input("EQ_phases_used_count", origin_element.find('quality').find('usedPhaseCount').text)

    smart_generate_input("EQ_station_used_count", origin_element, 'quality', 'usedStationCount')
    # generate_input("EQ_station_used_count", origin_element.find('quality').find('usedStationCount').text )

    smart_generate_input("EQ_max_azimuthal_gap", origin_element, 'quality', 'azimuthalGap', 3)
    # smart_generate_input("minHorizontalUncertainty",origin_element,'uncertainty','minHorizontalUncertainty')

    #გასარკვევია 
    # if origin_element.find('uncertainty').find('minHorizontalUncertainty') is not None:
    # 	min_horizontal_ancertaint = origin_element.find('uncertainty').find('minHorizontalUncertainty').text
    # 	max_horizontal_ancertaint = origin_element.find('uncertainty').find('maxHorizontalUncertainty').text
    # 	avarage = float(min_horizontal_ancertaint) + float(max_horizontal_ancertaint) / 2
    # 	avarage1 = math.sqrt((float(min_horizontal_ancertaint) * 2 ) + (float(max_horizontal_ancertaint) * 2 ))
    # 	print('aris')
    # 	print('min_horizontal_ancertainty : ',origin_element.find('uncertainty').find('minHorizontalUncertainty').text)
    # 	print('max_horizontal_ancertainty : ',origin_element.find('uncertainty').find('maxHorizontalUncertainty').text)
    # 	print(avarage)
    # 	print(avarage1)
    # else:
    # 	print('ar aris')

    
    picked_stations()
    calculated_magnitudes()
    print(STATIONS)







    
