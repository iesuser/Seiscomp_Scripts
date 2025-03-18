#!/usr/bin/env python3
import os
import sys
import re
import xml.etree.ElementTree as ET
import subprocess
import time

import logging
from logging.handlers import RotatingFileHandler

# იწერება კონფიგურაცია, რომლითაც მონაცემს წამოიღებს მიწისძვრის შესახებ
SERVER_IP = 'localhost'
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
EVENT_ID = sys.argv[2]

# გაშვებული სკრიპტის მისამართი
TEMP_DIR_PATH = SCRIPT_PATH + "/temp"
if not os.path.isdir(TEMP_DIR_PATH):
    os.mkdir(TEMP_DIR_PATH)

# log-ების მისამართი
LOGS_DIR_PATH = SCRIPT_PATH + "/logs"
if not os.path.isdir(LOGS_DIR_PATH):
    os.mkdir(LOGS_DIR_PATH)

# xml-ის და html-ის მისამართები, ასევე ბრაუზერი, რომლითან გახსნის html-ს 
XML_PATH = TEMP_DIR_PATH + "/eq_log.xml"
HTML_FILE_PATH = TEMP_DIR_PATH + "/redirectPostEq.html"
BROWSER = "firefox"

# 4 ასევე მანძილის გრადუსებიდან კილომეტრებში გადასაყვანად ვიყენებთ 111.19492664455873 გამრავლებას რამდენად სწორია ?? 
KILOMETER_DEVIDED_DEGREE_RATIO = 111.19492664455873

# იქმნება dictionary-ები, რომლებიც სეისკომპში არსებულ მონაცამებს გადათარგმნის ისეთ მონაცემებად, რომელსაც სერვერზე php სკრიპტი წაიკითხავს
SOFTWARE_NAMES = {'LOCSAT':'LocSAT(Seiscomp)'}
WAVE_TYPES = {'P':'Px'}

MAGNITUDE_TYPES = {'MLv':'mlv', 'MLh':'mlh', 'mb':'mb', 'ML':'ml', 'M':'M' }

# იქმენა ცარიელი ცვლადები, რომლებშიც შემდგომ შეივსება მონაცემები
FORM_LIST = []
STATIONS = {}

# logging-ის კონფიგურაცია
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

# ეს ფუნქცია პასუხისმგებელია xml-ის დაგენერირებაზე სეისკომპიდან გადმოცემული event_id-ით
def xml_dump(xml_path, event_id, server_ip):
    # seiscomp exec scxmldump -APMfmp -o /home/sysop/Code/Seiscomp_Scripts/import_eq2iesdata/temp/eq_log.xml -E grg2025fary -d localhost
    command = f'seiscomp exec scxmldump -APMfmp -o {xml_path} -E {event_id} -d {server_ip}'
    try:
        subprocess.run(command, check=True, shell=True )
        logging.debug(f'<xml_dump - xml წარმატებით დაგენერირდა>')
    except subprocess.CalledProcessError as e:
        # print("Error:", e)
        logging.critical(f'<xml_dump - xml-ის დაგენერირების დროს დაფიქსირდა შეცდომა: {e}>')
        sys.exit(1)

# ეს ფუნქცია მთავარ origin მონაცემებს გაპარსავს xml-დან
def picked_earthquake_origin():
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

    logging.debug(f'<picked_earthquake_origin - smart input-ები წარმატებით დაგენერირდა>')

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
    result = day + "-" + months[int(month)-1] + "-" + year + "_"  + HH + ':' + MM + ':' + ss + '.' + msec
    logging.debug(f'<convert_seiscomp_time_to_shm_time - დროის ფორმატი წარმატებით გარდაიქმნა: {result}>')
    return result

def convert_magnitude_name(magnitude):
    magnitude_name_lowercase = magnitude.lower()
    for key, value in MAGNITUDE_TYPES.items():
        if key.lower() == magnitude_name_lowercase:
            return value

    # print(f'ERROR: This Magnitude Type: {magnitude} does not exist in iesdata.iliauni.edu.ge')
    logging.critical(f'{magnitude}, მაგნიტუდის ტიპი {magnitude} არ არსებობს iesdata.iliauni.edu.ge-ზე')
    return None

def get_eq_min_max_value(magnitude_type):
	mag_min_value = mag_max_value = None
	magnitude_values = []
	for key, station in STATIONS.items():
		if 'magnitudes' in station and magnitude_type in station['magnitudes']:
			for mag_type, mag_value in station['magnitudes'][magnitude_type].items():
				magnitude_values.append(float(mag_value))
	if magnitude_values:
		mag_min_value = min(magnitude_values)
		mag_max_value = max(magnitude_values)

	return mag_min_value, mag_max_value

# stations ლექსიკონიდან station_code სადგურისთვის პპოულობს ისეთ ტალღებს რომლებმაც დათვლაში მიიღეს მონაწილეობა
# და აბრუნებს დროის გადახრას (timeResidual) p და s ტიპის ტალღებისთვის
def get_wave_time_residuals(station_code):
	p_wave_time_residual = None
	s_wave_time_residual = None

	for wave_type in STATIONS[station_code]['arrivals']:
		if wave_type[:1].lower() == 'p' and int(STATIONS[station_code]['arrivals'][wave_type]['weight']) > 0 \
		and 'timeResidual' in STATIONS[station_code]['arrivals'][wave_type].keys():
			p_wave_time_residual = STATIONS[station_code]['arrivals'][wave_type]['timeResidual']
		if wave_type[:1].lower() == 's' and int(STATIONS[station_code]['arrivals'][wave_type]['weight']) > 0 \
		and 'timeResidual' in STATIONS[station_code]['arrivals'][wave_type].keys():	
			s_wave_time_residual = STATIONS[station_code]['arrivals'][wave_type]['timeResidual']

	if p_wave_time_residual is not None:
		p_wave_time_residual = round(float(p_wave_time_residual), 4)

	if s_wave_time_residual is not None:
		s_wave_time_residual = round(float(s_wave_time_residual), 4)

	return p_wave_time_residual, s_wave_time_residual

# ფუნქცია აგენერირებს input-ებს მიწოდებული name(სახელი) და value(მნიშვნელობა) მნიშვნელობებით
def generate_input(name, value, func_name='generate_input'):
    FORM_LIST.append("<input name='" + str(name) + "' type='text' value='" + str(value) + "' />")
    logging.debug(f'<{func_name} - name: {name}; value: {value}>')

# ფუნქცია xml-ს გაპარსავს, ხოლო შემდგომ დააგენერირებს input-ებს generate_input ფუნქციის გამოყენებით
def smart_generate_input(name, element,first_child, second_child, round_number = None, convert_time_format = False):
	# xml-ს გაპარსვა სასურველი მონაცემების გამოყენებით
    if element.find(first_child) is not None and element.find(first_child).find(second_child) is not None:
        value = element.find(first_child).find(second_child).text
        if round_number is not None:
            value = round(float(value), round_number)
        if convert_time_format:
            value = convert_seiscomp_time_to_shm_time(value)

        generate_input(name, value, func_name='smart_generate_input')

# ფუნქცია აგენერირებს html გვერდს მიწოდებული form(ფორმის) მიხედვით
def generate_html():
    # იქმნება html-ისთვის ფორმა FORM_LIST ცვლადში არსებული მონაცემებით
    form = f"<form>\n" + "\n".join(FORM_LIST) + "\n</form>"
    # იქმნება string ცვლადი html, რომელიც შემდგომ ჩაიწერება html-ის ფაილში
    html = f"""<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.0 Transitional//EN' 'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'>
<html xmlns='http://www.w3.org/1999/xhtml'>
<head>
<meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
<title>data input</title>
</head>
<body>
<form name='postEqForm' action='https://10.0.0.237/admin/eq/getPostEq.php' method='post' style='display:none'>
{form}
</form>
<script>
        document.postEqForm.submit();
</script>
</body>
</html> """
    # ქმნის html-ის ფაილს და წერს ცვლად html-ში არსებულ მონაცემს
    html_file = open(HTML_FILE_PATH, "w")
    html_file.write(html)
    html_file.close()
    # html-ის ფაილს ხსნის ბრაუზერში, რომელიც მონაცემს აგზავნის iesdata-ზე (10.0.0.237)
    os.system(BROWSER + " " + HTML_FILE_PATH)
    time.sleep(2)
    # თუ html-ის ფაილი არსებობს, წაშლის მას
    if os.path.isfile(HTML_FILE_PATH):
        os.remove(HTML_FILE_PATH)

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
                STATIONS[station_code]['arrivals'][phase]['weight'] = ''

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

def generate_magnitudes_input():
    # მიწისძვრის მაგნიტუდების წაკითხვა და input-ების დაგენერირება
    # მიწისძვრის მაგნიტუდების მინიმალური და მაქსიმალური მნიშვნელობების წასაკითხათ აუცილებელია
    # stations სადგურების ლექსიკონი იყოს შევსებული, ამიტომ ვაგენერირებთ stations ლექსიკონის შევსების მერე
    magnitudes =  origin_element.findall('magnitude')
    generate_input("EQ_magLength", len(magnitudes))
    magnitude_index = 0
    for magnitude in magnitudes:
        magnitude_type = convert_magnitude_name(magnitude.find('type').text)
        generate_input("EQ_mag" + str(magnitude_index) + "_name", magnitude_type)
        generate_input("EQ_mag" + str(magnitude_index) + "_value", round(float(magnitude.find('magnitude').find('value').text), 3))
        magnitude_uncertainty = round(float(magnitude.find('magnitude').find('uncertainty').text), 3) if magnitude.find('magnitude').find('uncertainty') is not None else ""
        generate_input("EQ_mag" + str(magnitude_index) + "_uncertainty", magnitude_uncertainty )
        generate_input("EQ_mag" + str(magnitude_index) + "_number", magnitude.find('stationCount').text)
        mag_min_value, mag_max_value = get_eq_min_max_value(magnitude_type)
        if mag_min_value is not None:
            generate_input("EQ_mag" + str(magnitude_index) + "_min", mag_min_value)
        if mag_max_value is not None:
            generate_input("EQ_mag" + str(magnitude_index) + "_max", mag_max_value)
        magnitude_index += 1

def generate_stations_magnitudes():
    # სადგურის მაგნიტუდების input-ების დაგენერირება
    station_index = 0
    for station_code in STATIONS:
        st = 'ST' + str(station_index) + '_'
        generate_input(st + "name", station_code)
        generate_input(st + "azimuth", STATIONS[station_code]['azimuth'])
        generate_input(st + "distance", STATIONS[station_code]['distance'])

        p_wave_time_residual,s_wave_time_residual = get_wave_time_residuals(station_code)
        if p_wave_time_residual is not None:
            generate_input(st + "residual_origin_time_p", p_wave_time_residual)
        if s_wave_time_residual is not None:
            generate_input(st + "residual_origin_time_s", s_wave_time_residual)	
        if p_wave_time_residual is not None or s_wave_time_residual is not None:
            generate_input(st + "used_for_calculation", 'Yes')
        else:
            generate_input(st + "used_for_calculation", 'No')
        # print(STATIONS[station_code]['magnitudes'])
        mag_index = 0
        #+ შევამოწმოთ სადგურის მაგნიტუდების შესახებ ინფორაცია გვაქვს თუ არადა შემდეგ გავიაროთ ციკლი ინფორმაციის წასაკითხად
        if 'magnitudes' in STATIONS[station_code]:
            for magnitude_type in STATIONS[station_code]['magnitudes']:
                stm = st + "mag" + str(mag_index) + "_"
                generate_input(stm + "name", convert_magnitude_name(magnitude_type))
                generate_input(stm + "value", STATIONS[station_code]['magnitudes'][magnitude_type]['value'])
                # თუ სადგურის მაგნიტუდების residual-ები არსებოს მაშინ დააგენერიროს input-ები
                if 'residual' in STATIONS[station_code]['magnitudes'][magnitude_type]:
                    generate_input(stm + "residual", STATIONS[station_code]['magnitudes'][magnitude_type]['residual'])
                if 'amplitude' in STATIONS[station_code]['magnitudes'][magnitude_type]:
                    pass
                    # print('yes')	
                mag_index += 1 
        #+ input-ის გენრაცია მაშინ როცა magnitude-ს ლექსიკონი არსებობს 
        if 'magnitudes' in 	STATIONS[station_code]:
            generate_input(st + "magLength" , len(STATIONS[station_code]['magnitudes']))
            

        #სადგურის ტალღების inpute-ების დაგენერირება 		
        arrival_index = 0
        for phase_name in STATIONS[station_code]["arrivals"]:
            stw = st + 'wave' + str(arrival_index) + '_'
            generate_input(stw + 'name', phase_name)
            generate_input(stw + 'time', STATIONS[station_code]["arrivals"][phase_name]['time'])
            generate_input(stw + 'weight', STATIONS[station_code]["arrivals"][phase_name]['weight'])
            generate_input(stw + 'used_for_calculation', STATIONS[station_code]["arrivals"][phase_name]['used_for_calculation'])
            arrival_index += 1

        generate_input(st + 'waveLength', len(STATIONS[station_code]["arrivals"]))
        station_index += 1
    generate_input("ST_number", station_index)

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


    picked_earthquake_origin()    
    picked_stations()
    calculated_magnitudes()
    generate_magnitudes_input()
    generate_stations_magnitudes()
    generate_html()

    # print(STATIONS)
