#!/usr/bin/env python3
import os
import sys
import re
import xml.etree.ElementTree as ET
import subprocess
import shutil  # Import the shutil module

server_ip = 'localhost'
script_path = os.path.dirname(os.path.abspath(__file__))
event_id = sys.argv[2]


def xml_dump(xml_path, event_id, server_ip):
    # seiscomp exec scxmldump -APMfmp -o /home/sysop/Code/Seiscomp_Scripts/import_eq2iesdata/temp/eq_log.xml -E grg2025fary -d localhost
    command = f'seiscomp exec scxmldump -APMfmp -o {xml_path} -E {event_id} -d {server_ip}'
    try:
        subprocess.run(command, check=True, shell=True )
    except subprocess.CalledProcessError as e:
        print("Error:", e)
        sys.exit(1)


if __name__ == '__main__':
    """
        გვჭირდება სკრიპტის სამი ნაწილი
        1) XML ფაილის დაგენერირება სეისკომპიდან.
        2) XML ფაილის სწორად გაპარსვა და საჭირო ინფორმაციის ამოღება
        3) XML ფაილიდან ამოღებული ინფორმაციის გადაცემა PHP ფაილისთვის
    """

    # გაშვებული სკრიპტის მისამართი
    temp_dir_path = script_path + "/temp"
    if not os.path.isdir(temp_dir_path):
        os.mkdir(temp_dir_path)

    xml_path = temp_dir_path + "/eq_log.xml"
    html_file_path = temp_dir_path + "/redirectPostEq.html"

    # 1) XML ფაილის დაგენერირება სეისკომპიდან scxmldump-ის გამოყენებით .
    xml_dump(xml_path, event_id, server_ip)