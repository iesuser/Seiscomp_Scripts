#!/usr/bin/env python3
# Pipeline:
# 1) SeisComP-დან მოვლენის XML წამოღება (scxmldump)
# 2) XML-დან ძირითადი პარამეტრების ამოღება/დამრგვალება
# 3) ShakeMap event-ის შექმნა/გაშვება (sm_create + shake)
# 4) საბოლოო პროდუქტების ელფოსტით გაგზავნა
import os
import sys
import re
import shlex
import xml.etree.ElementTree as ET
import subprocess

import ies_mail_sender

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
    # ეს სკრიპტი ხშირად იძახება wrapper-იდან, სადაც event_id მოდის მესამე არგუმენტად.
    return sys.argv[2] if len(sys.argv) > 2 else None

# ეს ფუნქცია პასუხისმგებელია xml-ის დაგენერირებაზე სეისკომპიდან გადმოცემული event_id-ით
def xml_dump(xml_path, event_id, server_ip):
    # seiscomp exec scxmldump -AMp -o /home/sysop/Code/Seiscomp_Scripts/generate_shakemap/temp/eq_log.xml -E ies2026duod -d localhost
    command = f'seiscomp exec scxmldump -AMp -o {xml_path} -E {event_id} -d {server_ip}'
    try:
        subprocess.run(command, check=True, shell=True)
        logging.debug(f'<xml_dump - xml წარმატებით დაგენერირდა>')
    except subprocess.CalledProcessError as e:
        # print("Error:", e)
        logging.critical(f'<xml_dump - xml-ის დაგენერირების დროს დაფიქსირდა შეცდომა: {e}>')
        sys.exit(1)

def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

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

    event_element = event_parameters_element.find('event')
    if event_element is None:
        raise ValueError("XML-ში event ტეგი ვერ მოიძებნა")

    origin_element = event_parameters_element.find('origin')
    if origin_element is None:
        raise ValueError("XML-ში origin ტეგი ვერ მოიძებნა")

    # XML მნიშვნელობები თავდაპირველად string-ებია;
    # ვაქცევთ float-ად მხოლოდ ვალიდაციის/დამრგვალებისთვის.
    mag = to_float(origin_element.findtext("magnitude/magnitude/value"))
    depth = to_float(origin_element.findtext("depth/value"))
    lat = to_float(origin_element.findtext("latitude/value"))
    lon = to_float(origin_element.findtext("longitude/value"))

    parsed_data = {
        "event_id": event_element.attrib.get("publicID"),
        "time": origin_element.findtext("time/value"),
        "longitude": round(lon, 5) if lon is not None else None,
        "latitude": round(lat, 5) if lat is not None else None,
        "depth_km": round(depth, 1) if depth is not None else None,
        "magnitude": round(mag, 3) if mag is not None else None,
    }
    
    return parsed_data

def run_sm_create(parsed_data):
    required_fields = ["event_id", "time", "longitude", "latitude", "magnitude"]
    missing_fields = [field for field in required_fields if parsed_data.get(field) in (None, "")]
    if missing_fields:
        raise ValueError(f"sm_create-სთვის აუცილებელი ველები აკლია: {', '.join(missing_fields)}")

    event_id = parsed_data["event_id"]

    # sm_create ქმნის event-ს ShakeMap პროფილში.
    # აქ გადაეცემა NETID, TIME, LON, LAT, DEPTH, MAG და LOCSTR.
    sm_create_cmd = (
        f'sm_create -f {event_id} '
        f'-e ies '
        f'{parsed_data["time"]} '
        f'{parsed_data["longitude"]} '
        f'{parsed_data["latitude"]} '
        f'{parsed_data["depth_km"]} '
        f'{parsed_data["magnitude"]} '
        f'" " -n'
    )

    # shake-ის ეტაპები: select -> assemble -> model -> contour -> mapping
    shake_cmd = f'echo {event_id} | shake {event_id} select assemble model contour mapping'

    print(sm_create_cmd)
    print(shake_cmd)

    conda_exe = os.environ.get("CONDA_EXE", "conda")
    bash_command = (
        # conda activate ეფექტურია მხოლოდ იმავე shell-ის კონტექსტში,
        # ამიტომ sm_create/shake უნდა გაეშვას ერთ bash -lc ბრძანებაში.
        f'eval "$({shlex.quote(conda_exe)} shell.bash hook)" '
        f'&& conda activate shakemap '
        f'&& {sm_create_cmd} '
        f'&& {shake_cmd}'
    )

    subprocess.run(["/bin/bash", "-lc", bash_command], check=True)

    print(f'ShakeMap სრულად გაეშვა event_id={event_id}')
    logging.info("ShakeMap სრულად გაეშვა event_id=%s", event_id)


def send_email_with_attachments(event_id):
    mail_list_file_path = os.path.join(SCRIPT_PATH, "mail_list")

    email_title = f"მიწისძვრა - {event_id}"
    email_message = f'''
    ShakeMap მზად არის event: {event_id} შესამოწმებლად და შეგიძლიათ ნახოთ shake_map-ის ფოლდერში.

    დეტალური ინფორმაცია მიწისძვრის შესახებ:\n\n
    Event ID: {event_id}
    Time: {parsed_data["time"]}
    Location: {parsed_data["latitude"]}, {parsed_data["longitude"]}
    Depth: {parsed_data["depth_km"]} km
    Magnitude: {parsed_data["magnitude"]}
'''

    base_path = f"/home/sysop/shakemap_profiles/default/data/{event_id}/current/products"

    # ფაილები
    attachments = [
        os.path.join(base_path, "pga.jpg"),
        os.path.join(base_path, "pgv.jpg"),
        os.path.join(base_path, "intensity.jpg"),
    ]

    # მხოლოდ არსებული ფაილები
    existing_files = [f for f in attachments if os.path.exists(f)]

    if not existing_files:
        logging.error("არცერთი attachment ვერ მოიძებნა")
        return

    ies_mail_sender.send_mail(
        mail_list_file_path,
        email_title,
        email_message,
        attachments=existing_files
    )

    logging.info(f"მეილი გაიგზავნა: {event_id}")


if __name__ == '__main__':
    # Entry point:
    # 1) XML dump -> 2) parse -> 3) ShakeMap -> 4) email notification
    event_id = get_event_id_from_argv()
    mail_list_file_path = os.path.join(SCRIPT_PATH, "mail_list")
    email_title = "ახალი მიწისძვრის შესახებ ინფორმაცია"
    email_message = "ახალი მიწისძვრის შესახებ ინფორმაცია დაგენერირდა და შეგიძლიათ ნახოთ shake_map-ის ფოლდერში."

    if event_id:
        xml_dump(XML_PATH, event_id, SERVER_IP)

    if not os.path.exists(XML_PATH):
        logging.critical(f'XML ფაილი ვერ მოიძებნა: {XML_PATH}')
        sys.exit(1)

    try:
        parsed_data = parse_downloaded_xml(XML_PATH)
        print(parsed_data)

        run_sm_create(parsed_data)

        send_email_with_attachments(event_id)

    except Exception as exc:
        logging.critical(f'XML parse შეცდომა: {exc}')
        sys.exit(1)