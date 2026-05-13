#!/home/sysop/scripts/seiscomp_event/venv/bin/python3
# -*- coding: utf-8 -*-

import os, requests, sys
from datetime import datetime, timedelta
import functions
import ies_mail_sender
import ies_sms_sender

# მინიმუმი მაგნიტუდის მნიშვნელობა რის ზემოთაც ვაგზავნით შეტყობინებას მიწისშვრის შესახებ თუ ეპიცენტრი საქართველოს ფარგლებს შიგნითაა.
min_georgia_magnitude = 3.0
# მინიმუმი მაგნიტუდის მნიშვნელობა რის ზემოთაც ვაგზავნით შეტყობინებას მიწისშვრის შესახებ თუ ეპიცენტრი თბილისის ფარგლებს შიგნითაა.
min_tbilisi_magnitude = 2.8
# სკრიპტი ბეჭდავდეს თუ არა ტერმინალში
functions.printing = False
# სკრიპტი წერდეს თუ არა log ფაილში
functions.write_in_log = True
# log ფაილის სახელი
functions.log_filename = "log"

# მიწისძვრა გამოქვეყნდეს თუ არა ies.iliauni.edu.ge -ზე
publish_eq_to_ies_iliauni = True

testing = False

script_path = os.path.dirname(os.path.realpath(__file__))
# ფაილის მისამართი სადაც მითითებულია ელ-ფოსტები
mail_list_file_path = script_path + "/" + "mail_list"
staff_mail_list_filename = "staff_mail_list"

# ფაილის მისამართი სადაც მითითებულია მობილურის ნომრები. number_list ფაილში წერია ყველა ნომერი.
# staff_number_list ფაილში წერია მხოლოდ თანამშრომლების ნომრები
sms_list_file_path = script_path + "/" + "number_list"
staff_number_list_filename = "staff_number_list"

if testing:
    mail_list_file_path = script_path + "/testing/" + "test_mail_list"
    staff_mail_list_filename = "testing/test_mail_list"

    sms_list_file_path = script_path + "/testing/" + "test_number_list"
    staff_number_list_filename = "testing/test_number_list"

functions.print_and_log('გაეშვა სკრიპტი')

# scvoice - ის მიერ გამოგზავნილი პარამეტრის(public_event_id)მიღება
public_event_id = sys.argv[3]
functions.print_and_log('Event_ID: ' + str(public_event_id))
# აქ ხდება GetParamiter ფუნქციით მიწისძვრის პარამეტრების წაკითხვა ბაზიდან
try:
    orgTime, orgLat, orgLon, orgDepth, orgEvMode, magnitudes = functions.GetParamiter(public_event_id)
    # orgTime = '2022-11-29 23:57:51'
    # orgLat = 38.79
    # orgLon = 44.88
    # orgDepth = 8
    # orgEvMode = 'Automatic'
    # magnitudes = {'ML':13}
    # print(magnitudes)

except Exception as ex:
    functions.print_and_log("დასრულდა სკრიპტის მუშაობა\n")
    exit(1)


# მისიძვრის დროის(UTC) ლოკალურ დროში გადაყვანა
localOrgTime = datetime.strptime(orgTime, "%Y-%m-%d %H:%M:%S") + timedelta(hours=4)

# მაგნიტუდების ლექსიკონიდან მაგნიტუდის არჩევა
mType, mag = functions.choose_prefered_magnitude(magnitudes)
# magnitudis mnishvnelobis damrgvalebea measedebamde
mag = round(mag, 2)
# საწყისი sms და email შეტყობინების ტექსტი
#message = "Staging Server.\n" + orgEvMode.capitalize() + ": " + str(localOrgTime) + ". mag=" + str(mag) + mType + ". "
message = orgEvMode.capitalize() + ": " + str(localOrgTime) + ". mag=" + str(mag) + mType + ". "

# შევამოწმოთ მიწისძვრის ეპიცენტრი არის თუ არა საქართველოში
if functions.inBorder(orgLat, orgLon, "border_georgia"):
    message = message + "საქართველო."
    if mag >= min_georgia_magnitude:
        message = message + functions.findNCity(orgLat, orgLon)
    else:
        if functions.inBorder(orgLat, orgLon, "subborder_tbilisi"):
            if mag >= min_tbilisi_magnitude:
                message = message + functions.findtbilisi(orgLat, orgLon, 0)
            else:
                eq_text = "(კერის დრო = %s, განედი = %f, გრძედი = %f, სიღრმე = %f, მაგნიტუდა = %f)" % (orgTime, orgLat, orgLon, orgDepth, mag)
                log_text = "მიწისძვრას %s არ ვაგზავნით, რადგან ეპიცენტრი იყო თბილისში და მაგნიტუდა " % eq_text
                log_text += "არ აღემატებოდა %f-ს" % float(min_tbilisi_magnitude)
                functions.print_and_log(log_text)
                functions.print_and_log("დასრულდა სკრიპტის მუშაობა\n")
                exit(1)
        else:
            bor_min_dis = functions.borderMinDistance(orgLat, orgLon, "subborder_tbilisi")
            min_tbilisi_acceleration = functions.calculate_acceleration(min_tbilisi_magnitude, 0, 0)
            acceleration = functions.calculate_acceleration(mag, bor_min_dis, orgDepth)
            if acceleration >= min_tbilisi_acceleration:
                message = message + functions.findtbilisi(orgLat, orgLon, bor_min_dis)
            else:
                eq_text = "(კერის დრო = %s, განედი = %f, გრძედი = %f, სიღრმე = %f, მაგნიტუდა = %f)" % (orgTime, orgLat, orgLon, orgDepth, mag)
                log_text = "მიწისძვრას %s არ ვაგზავნით, რადგან ეპიცენტრი იყო საქართველოში და მაგნიტუდა არ აღემატებოდა %f-ს " % (eq_text, float(min_georgia_magnitude))
                log_text += "ასევე მიწისძვრა არ იყო თბილისთან იმდენად ახლოს ან იმდენად ძლიერი რომ მისი აჩქარება თბილისში მეტი ყოფილიყო თბილისში მომხდარ მიწისძვრის "
                log_text += "აჩქარებაზე რომლის მაგნიტუდაც იქნებოდა %f" % float(min_tbilisi_magnitude)
                functions.print_and_log(log_text)
                functions.print_and_log("დასრულდა სკრიპტის მუშაობა\n")
                exit(1)
else:  # tu sazgvargaret aris
    bor_min_dis = functions.borderMinDistance(orgLat, orgLon, "border_georgia")
    min_georgia_acceleration = functions.calculate_acceleration(min_georgia_magnitude, 0, 0)
    acceleration = functions.calculate_acceleration(mag, bor_min_dis, orgDepth)
    if acceleration >= min_georgia_acceleration:
        message = message + functions.findCountry(orgLat, orgLon, bor_min_dis)
        message = message + functions.findNCity(orgLat, orgLon)
    else:
        min_georgia_acceleration = 0.004
        # acceleration_100km_from_georgia = functions.calculate_acceleration(mag, bor_min_dis - 100 , orgDepth)
        if (bor_min_dis <= 100 and mag >= min_georgia_magnitude) or \
           (bor_min_dis > 100 and functions.calculate_acceleration(mag, bor_min_dis - 100 , orgDepth) >= min_georgia_acceleration):
            message = "STAFF ONLY.\n" + message
            message = message + functions.findCountry(orgLat,orgLon,bor_min_dis)
            message = message + functions.findNCity(orgLat,orgLon)
            sms_list_file_path = script_path + "/" + staff_number_list_filename
            mail_list_file_path = script_path + "/" + staff_mail_list_filename
            publish_eq_to_ies_iliauni = False
            functions.print_and_log("მიწისძვრის ინფორმაცია იგზავნება მხოლოდ თანამშრომლებთან")
        else:
            eq_text = "(კერის დრო = %s, განედი = %f, გრძედი = %f, სიღრმე = %f, მაგნიტუდა = %f)" % (orgTime, orgLat,  orgLon, orgDepth, mag)
            log_text = "მიწისძვრას %s არ ვაგზავნით, რადგან ეპიცენტრი იყო საქართველოს საზღვარს გარეთ და არ იყო საზღვართან " % eq_text
            log_text += "იმდენად ახლოს ან იმდენად ძლიერი რომ მისი აჩქარება საზღვართან მეტი ყოფილიყო საქართველოში მომხდარ მიწისძვრის აჩქარებაზე "
            log_text += "რომლის მაგნიტუდაც იქნებოდა %f" % float(min_georgia_magnitude)
            functions.print_and_log(log_text)
            functions.print_and_log("დასრულდა სკრიპტის მუშაობა\n")
            exit(1)

functions.ies_cursor.close()
functions.ies_db.close()
functions.print_and_log('Message: ' + message)

# google ის ლინკი მიწისძვრის კორდინატებით, რომელიც გაიგზავნება მიწისძვრის შეტყობინებასთან ერთად
google_link_with_eq_location = f"https://www.google.com/maps/place/{str(round(orgLat, 2))},{str(round(orgLon, 2))}"
message = message + "\n" + google_link_with_eq_location

# წავიკითხოდ მაგნიტუდების ლექსიკონი 
def send_eq_to_iesdata(publish_eq_to_ies_iliauni=True):
    functions.print_and_log('იწყება მიწისძვრის გაგზავნა iesdata.iliauni - ზე')
    site_script_parameters = {
                "event_id": public_event_id,
                "uccur_datetime": orgTime,
                "latitude": orgLat,
                "longitude": orgLon,
                "depth": orgDepth,
                "evMode": orgEvMode,
                "mag_length": len(magnitudes),
                "publish_eq_to_ies_iliauni": publish_eq_to_ies_iliauni}
    index = 0
    for mag_type, mag_value in magnitudes.items():
        site_script_parameters.update({"mag_type" + str(index): mag_type, "mag_value" + str(index): mag_value})
        index += 1
    # გავაგზავნოთ iesdata.iliauni.edu.ge - ზე
    iessdata_url = "https://10.0.0.237/admin/eq/auto_add_eq.php"
    ies_response = requests.get(iessdata_url, verify=False, params=site_script_parameters, timeout=120)
    if not ies_response.ok:
        functions.print_and_log('iesdata response: ' + str(ies_response.status_code) + ':' + ies_response.reason)
    functions.print_and_log(ies_response.text)
    functions.print_and_log('დასრულდა მიწისძვრის გაგზავნა iesdata.iliauni - ზე')


def send_eq_sms():
    ies_sms_sender.log_filename = "log"
    ies_sms_sender.send_sms(message=message, numbers_file_path=sms_list_file_path, use_gsm_modem=True, use_magti=True, use_smsoffice=True)


def send_eq_to_mail():
    functions.print_and_log('იწყება მიწისძვრის გაგზავნა email - ზე')
    email_title = "Earthquake - Automatic: %s. mag=%s%s" % (localOrgTime, mag, mType)
    email_message = message + '\nhttps://ies.iliauni.edu.ge/?page_id=121\n\n\nილიას სახელმწიფო უნივერსიტეტი\nდედამიწის შემსწავლელ მეცნიერებათა ინსტიტუტი და სეისმური მონიტორინგის ეროვნული ცენტრი'
    ies_mail_sender.send_mail(mail_list_file_path, email_title, email_message)
    functions.print_and_log('დასრულდა მიწისძვრის გაგზავნა email - ზე')


send_eq_to_iesdata(publish_eq_to_ies_iliauni)
send_eq_sms()
send_eq_to_mail()
functions.print_and_log("დასრულდა სკრიპტის მუშაობა\n")
