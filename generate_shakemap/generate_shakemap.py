#!/usr/bin/env python3
import os
import sys
import re
import xml.etree.ElementTree as ET
import subprocess

import logging
from logging.handlers import RotatingFileHandler

# იწერება კონფიგურაცია, რომლითაც მონაცემს წამოიღებს მიწისძვრის შესახებ
SERVER_IP = '192.168.11.250'
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

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

# logging-ის კონფიგურაცია
LOG_FILENAME = f'{LOGS_DIR_PATH}/generate_shakemap.log'
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


# safe helper: script is sometimes called without the event_id argument
def get_event_id_from_argv():
    return sys.argv[2] if len(sys.argv) > 2 else None


# ეს ფუნქცია პასუხისმგებელია xml-ის დაგენერირებაზე სეისკომპიდან გადმოცემული event_id-ით
def xml_dump(xml_path, event_id, server_ip):
    # seiscomp exec scxmldump -AMp -o /home/sysop/Code/Seiscomp_Scripts/generate_shakemap/temp/eq_log.xml -E ies2026duod -d localhost
    command = f'seiscomp exec scxmldump -AMp -o {xml_path} -E {event_id} -d {server_ip}'
    try:
        subprocess.run(command, check=True, shell=True )
        logging.debug(f'<xml_dump - xml წარმატებით დაგენერირდა>')
    except subprocess.CalledProcessError as e:
        # print("Error:", e)
        logging.critical(f'<xml_dump - xml-ის დაგენერირების დროს დაფიქსირდა შეცდომა: {e}>')
        sys.exit(1)


def parse_downloaded_xml(xml_path):
    with open(xml_path, "r", encoding="utf-8") as xml_file:
        xml_file_content = re.sub(' xmlns="[^"]+"', '', xml_file.read(), count=1)

    # String დან xml-ის "გაპარსვა"
    root = ET.fromstring(xml_file_content)

    # xml - ში origin ტეგის წაკითხვა
    event_parameters_element = root.find('EventParameters')
    if event_parameters_element is None and root.tag == 'EventParameters':
        event_parameters_element = root
    if event_parameters_element is None:
        raise ValueError("XML-ში EventParameters ტეგი ვერ მოიძებნა")

    origin_element = event_parameters_element.find('origin')
    if origin_element is None:
        raise ValueError("XML-ში origin ტეგი ვერ მოიძებნა")

    parsed_origin = {
        "publicID": origin_element.attrib.get("publicID"),
        "time": origin_element.findtext("time/value"),
        "latitude": origin_element.findtext("latitude/value"),
        "longitude": origin_element.findtext("longitude/value"),
        "depth_km": origin_element.findtext("depth/value"),
    }
    return parsed_origin


if __name__ == '__main__':
    # 1) XML ფაილის დაგენერირება სეისკომპიდან scxmldump-ის გამოყენებით .
    event_id = get_event_id_from_argv()
    if event_id:
        xml_dump(XML_PATH, event_id, SERVER_IP)

    if not os.path.exists(XML_PATH):
        logging.critical(f'XML ფაილი ვერ მოიძებნა: {XML_PATH}')
        sys.exit(1)

    try:
        parsed_origin = parse_downloaded_xml(XML_PATH)
        print(parsed_origin)
    except Exception as exc:
        logging.critical(f'XML parse შეცდომა: {exc}')
        sys.exit(1)