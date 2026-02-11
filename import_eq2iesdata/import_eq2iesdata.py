#!/usr/bin/env python
# -*- coding: utf-8 -*-
#############################################################
#                       README                              #
#############################################################
#epicentruli cdomilebebi tu gvinda iyos xml shi mashin      #
#scconfig-idan global-shi                                   #
#LOCSAT.enableConfidenceEllipsoid = true					#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#															#
#############################################################
import math
import os
import sys
import xml.etree.ElementTree as ET
import re
from datetime import time
import time
import json
if sys.version_info < (3,0):
	import Tkinter as tkinter
	import tkMessageBox as mbox
else:
	import tkinter
	import tkinter.messagebox as mbox



# 1 გავარკვიოთ სეისკომში თუ ითვლება ეპიცენტრული ცდომილება, 
# 2 location_code  ები გასარკვევია სეისკომპიდან როგორ წავიკითხოთ და გასარკვევია iesdata-ს მხარეს როგორ ხდება location_code ების მინიჭება. 
# 3 მიწისძვრის მაგნიტუდის დათვლის მეთოდი (მაგალითად treamed mean ან mean) iesdata-ზე ხო არ ჩავამატოთ? და აქედანაც შევძლებთ გადატანას
# 4 ასევე მანძილის გრადუსებიდან კილომეტრებში გადასაყვანად ვიყენებთ 111.19492664455873 გამრავლებას რამდენად სწორია ?? 
# 5 მაგნიტუდა M ითვლება სეისკომში და გადაგვაქვს როგორც ml გასარკვევია თუ ვიქცევით სწორად


# როდესაც scolv - დან ეშვება სკრიპტი ავტომატურად ემატება პარამეტრი მონიშნული origin -ის მიხედვით.
# თუ მონიშნული არ არის კონკრეტული Origin-ი . ამ შემთხვევაში event-დან იღებს ბოლო ორიგინს რომელიც 
# ავტომატურად არის დათვლილი (გამუქებულად ჩანს scolvSo)
kilometer_devided_degree_ratio = 111.19492664455873
magnitude_types = {'MLv':'mlv', 'MLh':'mlh', 'mb':'mb', 'M':'ml' }
wave_types = {'P':'Px'}
software_names = {'LOCSAT':'LocSAT(Seiscomp)'}
browser = "firefox"

genereted_form = ""
origin_id = sys.argv[1]
# გაშვებული სკრიპტის მისამართი
script_path = os.path.dirname(os.path.realpath(__file__))
temp_dir_path = script_path + "/temp"
if not os.path.isdir(temp_dir_path):
	os.mkdir(temp_dir_path)


xml_path = temp_dir_path + "/eq_log.xml"
html_file_path = temp_dir_path + "/redirectPostEq.html"



def convert_software_name(software):
	for key, value in software_names.items():
		if key == software:
			return value
	return 	software	

def convert_wave_name(wave):
	wave_name_lowercase = wave.lower()
	for key, value in wave_types.items():
		if key.lower() == wave_name_lowercase:
			return value
	return wave


#ეს ფუნქცია 
def convert_magnitude_name(magnitude):
	magnitude_name_lowercase = magnitude.lower()
	for key, value in magnitude_types.items():
		if key.lower() == magnitude_name_lowercase:
			return value
	print('magnitudis tipi ar arsebobs')
	window = tkinter.Tk()
	window.wm_withdraw()
	mbox.showinfo(magnitude,'მაგნიტუდის ტიპი' + " " + magnitude + " "  'არ არსებობს iesdata.iliauni.edu.ge-ზე')
	return magnitude

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



# ფუნქცია აგენერირებს html გვერდს მიწოდებული form(ფორმის) მიხედვით
def generate_html(form):
	return """<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.0 Transitional//EN' 'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'>
<html xmlns='http://www.w3.org/1999/xhtml'>
<head>
<meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
<title>data input</title>
</head>
<body>
<form name='postEqForm' action='http://10.0.0.237/admin/eq/getPostEq.php' method='post' style='display:none'>
%s</form>
<script>
        document.postEqForm.submit();
</script>
</body>
</html> """ % form

# ფუნქცია აგენერირებს input-ებს მიწოდებული name(სახელი) და value(მნიშვნელობა) მნიშვნელობებით
def generete_input(name, value):
	global genereted_form
	genereted_form += "<input name='" + str(name) + "' type='text' value='" + str(value) + "' />\n"


# stations ლექსიკონიდან station_code სადგურისთვის პპოულობს ისეთ ტალღებს რომლებმაც დათვლაში მიიღეს მონაწილეობა
# და აბრუნებს დროის გადახრას (timeResidual) p და s ტიპის ტალღებისთვის
def get_wave_time_residuals(station_code):
	global stations
	p_wave_time_residual = None
	s_wave_time_residual = None

	for wave_type in stations[station_code]['arrivals']:
		if wave_type[:1].lower() == 'p' and int(stations[station_code]['arrivals'][wave_type]['weight']) > 0 \
		and 'timeResidual' in stations[station_code]['arrivals'][wave_type].keys():
			p_wave_time_residual = stations[station_code]['arrivals'][wave_type]['timeResidual']
		if wave_type[:1].lower() == 's' and int(stations[station_code]['arrivals'][wave_type]['weight']) > 0 \
		and 'timeResidual' in stations[station_code]['arrivals'][wave_type].keys():	
			s_wave_time_residual = stations[station_code]['arrivals'][wave_type]['timeResidual']

	if p_wave_time_residual is not None:
		p_wave_time_residual = round(float(p_wave_time_residual), 4)

	if s_wave_time_residual is not None:
		s_wave_time_residual = round(float(s_wave_time_residual), 4)

	return p_wave_time_residual, s_wave_time_residual

os.system("~/seiscomp3/bin/seiscomp exec scxmldump -APMfmp -O " + sys.argv[1] +  " -d localhost > " + xml_path)


file = open(xml_path, "r")
xml_file_content = xmlstring = re.sub(' xmlns="[^"]+"', '', file.read(), count=1)

#String დან xml-ის "გაპარსვა"
root = ET.fromstring(xml_file_content)
#xml - ში origin ტეგის წაკითხვა
eventParameters_element =  root.find('EventParameters')
origin_element = eventParameters_element.find('origin')

# მიწისძვრის პარამეტრების წაკითხვა და input-ების დაგენერირება
#ამ ეტაპზე მოწმდება მიწისძვრა დათვლილია თუ არა რაიმე მეთოდით (მაგ:LOCSAT)
if origin_element.find('methodID') is not None:
	soft = convert_software_name(origin_element.find('methodID').text)
else:
	soft = 'Raw'	

# ფუნქცია აგენერირებს input-ებს
def smart_generete_input(name, element,first_child, second_child, round_number = None, convert_time_format = False):
	global genereted_form
	
	if element.find(first_child) is not None and element.find(first_child).find(second_child) is not None:
		value = element.find(first_child).find(second_child).text
		if round_number is not None:
			value = round(float(value), round_number)
		if convert_time_format:
			value = convert_seiscomp_time_to_shm_time(value)

		genereted_form += "<input name='" + str(name) + "' type='text' value='" + str(value) + "' />\n"

def get_eq_min_max_value(magnitude_type):
	global stations 
	mag_min_value = mag_max_value = None
	magnitude_values = []
	for key, station in stations.iteritems():
		if 'magnitudes' in station and magnitude_type in station['magnitudes']:
			for mag_type, mag_value in station['magnitudes'][magnitude_type].items():
				magnitude_values.append(float(mag_value))
	if magnitude_values:
		mag_min_value = min(magnitude_values)
		mag_max_value = max(magnitude_values)

	return mag_min_value, mag_max_value


generete_input("soft", soft )

smart_generete_input("EQ_time", origin_element, 'time', 'value', convert_time_format = True)
smart_generete_input("EQ_rms", origin_element, 'time', 'uncertainty', 3)
# generete_input("EQ_rms", round(float(origin_element.find('time').find('uncertainty').text), 3 ))


# generete_input("EQ_latitude", round(float(origin_element.find('latitude').find('value').text), 4 ))
smart_generete_input("EQ_rms", origin_element, 'latitude', 'value', 4)
smart_generete_input("EQ_err_lat", origin_element, 'latitude', 'uncertainty', 3)

smart_generete_input("EQ_latitude", origin_element, 'latitude', 'value', 4)
smart_generete_input("EQ_err_lat", origin_element, 'latitude', 'uncertainty', 3)
# generete_input("EQ_latitude", round(float(origin_element.find('latitude').find('value').text), 4 ))
# generete_input("EQ_err_lat", round(float(origin_element.find('latitude').find('uncertainty').text), 3))

smart_generete_input("EQ_longitude", origin_element, 'longitude', 'value', 4)
smart_generete_input("EQ_err_long", origin_element, 'longitude', 'uncertainty', 3)
# generete_input("EQ_longitude", round(float(origin_element.find('longitude').find('value').text), 4 ))
# generete_input("EQ_err_long", round(float(origin_element.find('longitude').find('uncertainty').text), 3 ))

smart_generete_input("EQ_depth", origin_element, 'depth', 'value', 3)
smart_generete_input("EQ_err_depth", origin_element, 'depth', 'uncertainty', 3)
# generete_input("EQ_depth", round(float(origin_element.find('depth').find('value').text), 3 ))
# generete_input("EQ_err_depth", round(float(origin_element.find('depth').find('uncertainty').text), 3))


smart_generete_input("EQ_phases_count", origin_element, 'quality', 'associatedPhaseCount', 3)
smart_generete_input("EQ_phases_used_count", origin_element, 'quality', 'usedPhaseCount', 3)
# generete_input("EQ_phases_count", origin_element.find('quality').find('associatedPhaseCount').text)
# generete_input("EQ_phases_used_count", origin_element.find('quality').find('usedPhaseCount').text)

smart_generete_input("EQ_station_used_count", origin_element, 'quality', 'usedStationCount')
# generete_input("EQ_station_used_count", origin_element.find('quality').find('usedStationCount').text )


smart_generete_input("EQ_max_azimuthal_gap", origin_element, 'quality', 'azimuthalGap', 3)
# smart_generete_input("minHorizontalUncertainty",origin_element,'uncertainty','minHorizontalUncertainty')

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


# ლექსიკონი სადაც შევინახავთ სადგურების მონაცემებს
stations = {}
# სადგურების წაკითხვა და input-ების გენერაცია
arrivals = origin_element.findall('arrival')
# ვავსებთ station ლექსიკონს იმ მიზნით რომ პიკები დაჯგუფდეს სადგურების მიხედვით რათა შემდგომში ადვილად შევძლოთ
# ინფუთების დაგენერირება
for arrival in arrivals:
	pick_id = arrival.find('pickID').text
	pick_element = eventParameters_element.find("*[@publicID='" + pick_id + "']")
	#სადგურის კოდი
	station_code = pick_element.find('waveformID').attrib['stationCode']

	# station ლექსიკონში ჩავამატოთ station_code გასაღები იმ შემთხვევაში თუ არ არსებობს უკვე
	if station_code not in stations:
		stations[station_code] = {}
	stations[station_code]['network'] = pick_element.find('waveformID').attrib['networkCode']
	stations[station_code]['channel'] = pick_element.find('waveformID').attrib['channelCode']

	if 'arrivals' not in stations[station_code]:
		stations[station_code]['arrivals'] = {}

	#წავიკითხოთ ტალღის სახელი
	phase = convert_wave_name(arrival.find('phase').text)

	stations[station_code]['azimuth'] = round(float(arrival.find('azimuth').text), 3)
	#+სადგურებიდან მანძილი გადადის გრადუსიდან კილომეტრში და ისე ხდება მნიშვნელობის შენახვა
	stations[station_code]['distance'] = round(float(arrival.find('distance').text) * kilometer_devided_degree_ratio, 3)
	stations[station_code]['arrivals'][phase] = {}
	#გასარკვევია როგორ გადავა iesdata-ზე 
	if arrival.find('timeResidual') is not None:
		stations[station_code]['arrivals'][phase]['timeResidual'] = arrival.find('timeResidual').text
	stations[station_code]['arrivals'][phase]['time'] = convert_seiscomp_time_to_shm_time(pick_element.find('time').find('value').text)
	if arrival.find('weight') is not None :
		stations[station_code]['arrivals'][phase]['weight'] = arrival.find('weight').text
		if int(arrival.find('weight').text) > 0 :
			stations[station_code]['arrivals'][phase]['used_for_calculation'] = "Yes"
		else:
			stations[station_code]['arrivals'][phase]['used_for_calculation'] = "No"	


#station ლექსიკონში მაგნიტუდების შევსება
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
		#print(station_code)
		#print(station_amplitude_value)
		#წავიკითხოთ მაგნიტუდის ტიპი და stations ლექსიკონში დავამატოთ შესაბამისი ახალი ლექსიკონი
		magnitude_type = convert_magnitude_name(stations_magnitude.find('type').text)
		if 'magnitudes' not in stations[station_code]:
			stations[station_code]['magnitudes'] = {}
		if 	magnitude_type not in stations[station_code]['magnitudes']:
			stations[station_code]['magnitudes'][magnitude_type] = {}
		# print(magnitude_type)
		# print(magnitude.find('magnitude').find('value').text)
		stations[station_code]['magnitudes'][magnitude_type]['value'] = round(float(stations_magnitude.find('magnitude').find('value').text), 2)
		#+ თუ სადგურის მაგნიტუდების residual-ები არის მაშინ შეივსოს ლექსიკონი შესაბამისი ინფორმაციით
		if stationMagnitudeContribution.find('residual') is not None:
			stations[station_code]['magnitudes'][magnitude_type]['residual'] = stationMagnitudeContribution.find('residual').text
		stations[station_code]['magnitudes'][magnitude_type]['amplitude'] = station_amplitude.find('amplitude').find('value').text
		

# მიწისძვრის მაგნიტუდების წაკითხვა და input-ების დაგენერირება
# მიწისძვრის მაგნიტუდების მინიმალური და მაქსიმალური მნიშვნელობების წასაკითხათ აუცილებელია
# stations სადგურების ლექსიკონი იყოს შევსებული, ამიტომ ვაგენერირებთ stations ლექსიკონის შევსების მერე
magnitudes =  origin_element.findall('magnitude')
generete_input("EQ_magLength", len(magnitudes))
magnitude_index = 0
for magnitude in magnitudes:
	magnitude_type = convert_magnitude_name(magnitude.find('type').text)
	generete_input("EQ_mag" + str(magnitude_index) + "_name", magnitude_type)
	generete_input("EQ_mag" + str(magnitude_index) + "_value", round(float(magnitude.find('magnitude').find('value').text), 3))
	magnitude_uncertainty = round(float(magnitude.find('magnitude').find('uncertainty').text), 3) if magnitude.find('magnitude').find('uncertainty') is not None else ""
	generete_input("EQ_mag" + str(magnitude_index) + "_uncertainty", magnitude_uncertainty )
	generete_input("EQ_mag" + str(magnitude_index) + "_number", magnitude.find('stationCount').text)
	mag_min_value, mag_max_value = get_eq_min_max_value(magnitude_type)
	if mag_min_value is not None:
		generete_input("EQ_mag" + str(magnitude_index) + "_min", mag_min_value)
	if mag_max_value is not None:
		generete_input("EQ_mag" + str(magnitude_index) + "_max", mag_max_value)
	magnitude_index += 1


# სადგურის მაგნიტუდების input-ების დაგენერირება
station_index = 0
for station_code in stations:
	st = 'ST' + str(station_index) + '_'
	generete_input(st + "name", station_code)
	generete_input(st + "azimuth", stations[station_code]['azimuth'])
	generete_input(st + "distance", stations[station_code]['distance'])

	p_wave_time_residual,s_wave_time_residual = get_wave_time_residuals(station_code)
	if p_wave_time_residual is not None:
		generete_input(st + "residual_origin_time_p", p_wave_time_residual)
	if s_wave_time_residual is not None:
		generete_input(st + "residual_origin_time_s", s_wave_time_residual)	
	if p_wave_time_residual is not None or s_wave_time_residual is not None:
		generete_input(st + "used_for_calculation", 'Yes')
	else:
		generete_input(st + "used_for_calculation", 'No')
	# print(stations[station_code]['magnitudes'])
	mag_index = 0
	#+ შევამოწმოთ სადგურის მაგნიტუდების შესახებ ინფორაცია გვაქვს თუ არადა შემდეგ გავიაროთ ციკლი ინფორმაციის წასაკითხად
	if 'magnitudes' in stations[station_code]:
		for magnitude_type in stations[station_code]['magnitudes']:
			stm = st + "mag" + str(mag_index) + "_"
			generete_input(stm + "name", convert_magnitude_name(magnitude_type))
			generete_input(stm + "value", stations[station_code]['magnitudes'][magnitude_type]['value'])
			# თუ სადგურის მაგნიტუდების residual-ები არსებოს მაშინ დააგენერიროს input-ები
			if 'residual' in stations[station_code]['magnitudes'][magnitude_type]:
				generete_input(stm + "residual", stations[station_code]['magnitudes'][magnitude_type]['residual'])
			if 'amplitude' in stations[station_code]['magnitudes'][magnitude_type]:
				print('yes')	
			mag_index += 1 
	#+ input-ის გენრაცია მაშინ როცა magnitude-ს ლექსიკონი არსებობს 
	if 'magnitudes' in 	stations[station_code]:
		generete_input(st + "magLength" , len(stations[station_code]['magnitudes']))
		

	#სადგურის ტალღების inpute-ების დაგენერირება 		
	arrival_index = 0
	for phase_name in stations[station_code]["arrivals"]:
		stw = st + 'wave' + str(arrival_index) + '_'
		generete_input(stw + 'name', phase_name)
		generete_input(stw + 'time', stations[station_code]["arrivals"][phase_name]['time'])
		generete_input(stw + 'weight', stations[station_code]["arrivals"][phase_name]['weight'])
		generete_input(stw + 'used_for_calculation', stations[station_code]["arrivals"][phase_name]['used_for_calculation'])
		arrival_index += 1

	generete_input(st + 'waveLength', len(stations[station_code]["arrivals"]))
	station_index += 1
generete_input("ST_number", station_index)


html_file = open(html_file_path, "w")
html_file.write(generate_html(genereted_form))
html_file.close()

# print(stations)
# if os.path.isfile(xml_path):
# 	os.remove(xml_path)

os.system(browser + " " + html_file_path)
time.sleep(2)

if os.path.isfile(html_file_path):
	os.remove(html_file_path)


