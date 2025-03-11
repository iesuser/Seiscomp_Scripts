#!/usr/bin/env python3
import os
import sys
import re
import xml.etree.ElementTree as ET
import subprocess
import shutil  # Import the shutil module

server_ip = 'localhost'
# Define the desired zoom level (adjust as needed)
zoom_level = 0
script_path = os.path.dirname(os.path.abspath(__file__))


# Execute scxmldump command to retrieve earthquake data

command = f'seiscomp exec scxmldump -PMfmp -o /home/sysop/Code/Seiscomp_Scripts/plot_eq2google_map/google_temp.xml -E {sys.argv[2]} -d {server_ip}'

try:
    subprocess.run(command, check=True, shell=True )
except subprocess.CalledProcessError as e:
    print("Error:", e)
    sys.exit(1)

xml_path = os.path.join(script_path, 'google_temp.xml')

# Read XML file and remove default namespace
with open(xml_path, "r") as file:
    xml_file_content = re.sub(' xmlns="[^"]+"', '', file.read(), count=1)

# Parse XML content
try:
    root = ET.fromstring(xml_file_content)
    eventParameters_element = root.find('EventParameters')
    origin_element = eventParameters_element.find('origin')
    EQ_latitude = origin_element.find('latitude').find('value').text
    EQ_longitude = origin_element.find('longitude').find('value').text
except (ET.ParseError, AttributeError) as e:
    print("Error parsing XML:", e)
    sys.exit(1)

# Open Google Maps with the earthquake's location
google_maps_url = "https://maps.google.com/maps?q={},{}".format(EQ_latitude, EQ_longitude)
# browser_command = "google-chrome" if shutil.which("google-chrome") else "firefox"
browser_command = "firefox" if shutil.which("firefox") else "google-chrome"
subprocess.run([browser_command, google_maps_url])

