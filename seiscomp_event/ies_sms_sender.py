# -*- coding: utf-8 -*-
import os, requests, datetime, re, time, json, pickle
#import gammu

# iesresource - საიტის gsm - ით სმს გასაგზავნი php failis მისამართი
ies_gsm_sms_sender_url = 'http://iesresource.iliauni.edu.ge/block/ies_gsm_sms_sender.php'
code = ""

# მაგთის სერვერის მისამართი, რომლითაც ვაგზავნით sms - ებს
magti_url = 'http://81.95.160.47/mt/oneway?'

# მაგთის სერვერის user - ი, 
magti_username = ''
# მაგთის სერვერის user - ის პაროლი
magti_password = ''

magti_track_url = "http://81.95.160.47/bi/track.php"


# smsoffice - ი
sms_offic_key = ''
sms_offic_url = 'https://smsoffice.ge/api/v2/send/'
# smsoffice_balance_url = f'https://smsoffice.ge/api/getBalance?key={sms_offic_key}'
smsoffice_balance_url = "http://smsoffice.ge/api/getBalance?key={}".format(sms_offic_key)
smsoffice_balance_min_warning_value = 5000
smsoffice_balance_check_time_interval = 6

# log ფაილის სახელი
log_filename = "ies_sms_sender_log"
# სკრიპტი ბეჭდავდეს თუ არა ტერმინალში
printing = True
# სკრიპტი წერდეს თუ არა log ფაილში
write_in_log = True
# გავიგოთ მისამართი საიდანაც გაეშვა ies_time_check.py სკრიპტი
script_path = os.path.dirname(os.path.realpath(__file__))


def init_gammu():
    try:
        # Create object for talking with phone
        state_machine = gammu.StateMachine()

        # Read the configuration from given file
        state_machine.ReadConfig()

        # Connect to the phone
        state_machine.Init()

        return state_machine
    except Exception as ex:
        print_and_log("შეცდომა gammu-ს ინიციალიზაციისას. Exception = {}".format(ex))
        return False


"""
ფუნქცია, რომელიც გადაცემულ message - ს ჩაწერს  მითტითებულ log ფაილში
ან დაბეჭდავს ტერმინალში
""" 
def print_and_log(message, empty_line=False):
    log_file_path = script_path + "/" + log_filename
    pid  = os.getpid()
    if printing is True:
        print("[" + datetime.datetime.now().strftime('%Y-%m-%d %T') + "] [" + str(pid) + "] " + message)
    if write_in_log is True:
        with open(log_file_path, "a") as log_file:
            if not empty_line:
                log_file.write("[" + datetime.datetime.now().strftime('%Y-%m-%d %T') + "] [" + str(pid) + "] " + message + "\n")
            else:
                log_file.write("\n")


"""
ფუნქცია გადაცემული ფაილის მისამართიდან კითხულობს ყველა ხაზზს და აბრუნებს ნომრების სიას 
"""
def read_numbers_from_file(numbers_file_path):
    if os.path.exists(numbers_file_path):
        with open(numbers_file_path, 'r') as numbers_file:
            lines =  numbers_file.readlines()
        numbers = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            line = line.split('#')[0].strip() 

            if re.match('^[0-9]{12}$',line):
                numbers.append(line)
            else:
                print_and_log("ფაილში მითითებული ნომერი ='{}' არასწორია".format(line))      
        if numbers :
            return numbers
        else:
            print_and_log("მითითებულ numbers_file_path='{}' ფაილში ვერ მოიძებნა ნომერი(ები) ".format(numbers_file_path))
            return []   
    else:
        print_and_log("numbers_file_path='{}' ფაილი არ არსებობს".format(numbers_file_path))
        return []


def read_numbers(numbers):
    if not numbers:
        return []
    if type(numbers) is list:
        return numbers
    numbers_list = numbers.split(',')
    numbers = []
    for number in numbers_list:
        number = number.strip()
        if re.match('^[0-9]{12}$',number):
            numbers.append(number)
        else:
            print_and_log("მითითებული ნომერი ='{}' არასწორია".format(number))      
    if numbers:
        return numbers
    else:
        return []


def send_sms(message='', numbers='', numbers_file_path='', use_gsm_modem=True, use_magti=True, use_smsoffice=True):
    numbers = read_numbers(numbers)
    if not numbers:
        numbers = read_numbers_from_file(numbers_file_path)


    if use_magti and numbers:
        numbers = send_sms_via_magti(message, numbers=numbers)

    if use_smsoffice and numbers:
        numbers = send_sms_via_smsoffice(message, numbers=numbers)
      
    if use_gsm_modem and numbers:
        send_sms_via_gsm_modem(message, numbers=numbers)    

    check_smsoffice_balance()                   
   


def send_sms_via_magti(message, numbers='', numbers_file_path='', try_number=1, time_until_next_try=1, request_timeout=1, time_until_tracking_sms=5):
    numbers = read_numbers(numbers)
    if not numbers:
        numbers = read_numbers_from_file(numbers_file_path)

    sent_message_ids_with_numbers = dict()
    failed_numbers = []
    print_and_log('იწყება მაგთის ლინკით sms-ების დაგზავნა')
    for try_index in range(1, try_number+1):
        for number in numbers:
            params = {'username': magti_username,
                      'password': magti_password,
                      'client_id': 643,
                      'service_id': 1,
                      'to': number,
                      'text': message,
                      'coding': 2}
            try:
                response = requests.get(magti_url, timeout=request_timeout, params=params)
                if not response.ok:
                    failed_numbers.append(number)
                    print_and_log("მითითებულ ნომერზე'{}' ვერ გაიგზავნა sms-ი. status_code = '{}', try_index = {}".format(number, response.status_code, try_index))
                    continue
                else:
                    status = response.text[:4]
                    if status != '0000':
                        failed_numbers.append(number)
                        print_and_log("მითითებულ ნომერზე'{}' ვერ გაიგზავნა sms-ი. response_text = '{}', try_index = {}".format(number, response.text, try_index))
                        continue
                    else:
                        sent_message_ids_with_numbers[number] = response.text.split('-')[1].strip()
            except Exception as ex:
                failed_numbers.append(number)
                print_and_log("მითითებულ ნომერზე'{}' ვერ გაიგზავნა sms-ი. try_index = {}.\n{} ".format(number,  try_index, str(ex)))

        if sent_message_ids_with_numbers:
            time.sleep(time_until_tracking_sms)
            for number, message_id in sent_message_ids_with_numbers.items():
                track_url_params = {'username': magti_username,
                                    'password': magti_password,
                                    'client_id': 643,
                                    'service_id': 1,
                                    'message_id': message_id
                                }
                track_response = requests.get(magti_track_url, timeout=request_timeout, params=track_url_params)
                
                if not track_response.ok:
                    failed_numbers.append(number)
                    print_and_log("მითითებულ ნომერზე '{}' ვერ  მოხერხდა sms სტატუსის შემოწმება")
                else:
                    if track_response.text.strip() in ['1','4','8'] :
                        print_and_log("მითითებულ ნომერზე '{}' sms-ი წარმატებით გაიგზავნა მაგთის ლინკით. track_response_text = '{}', try_index = {}".format(number, track_response.text.strip(), try_index))
                    else:
                        failed_numbers.append(number)
                        print_and_log("მითითებულ ნომერზე'{}' ვერ გაიგზავნა sms-ი. track_response_text = '{}', try_index = {}".format(number, track_response.text.strip(), try_index))
        
        if not failed_numbers:
            print_and_log("sms-ები დაიგზავნა წარმატებით. try_index = {}".format(try_index))
            break
        else:
            print_and_log("sms-ების დაგზავნა ვერ მოხერხდა {} ნომერთან. try_index = {}".format(len(failed_numbers), try_index))
            # numbers = failed_numbers.copy()
            numbers = list(failed_numbers)
            if try_index != try_number:
                failed_numbers = []
                time.sleep(time_until_next_try)
    print_and_log('დასრულდა მაგთის ლინკით sms-ების დაგზავნა')
    return failed_numbers




def send_sms_via_gammu(message, numbers='', numbers_file_path='', init=True, state_machine=None):
    print_and_log('იწყება gammu-თი sms-ების დაგზავნა')
    numbers = read_numbers(numbers)
    if not numbers:
        numbers = read_numbers_from_file(numbers_file_path)
    if init:
        state_machine = init_gammu()
        if not state_machine:
            return []

    smsinfo = {
        'Class': -1,
        'Unicode': True,
        'Entries':  [
            {
                'ID': 'ConcatenatedTextLong',
                'Buffer': message
            }
        ]}

    failed_numbers = []

    for number in numbers:
        try:
            # Encode messages
            encoded = gammu.EncodeSMS(smsinfo)

            # Send messages
            for message in encoded:
                # Fill in numbers
                message['SMSC'] = {'Location': 1}
                message['Number'] = '+' + number

                # Actually send the message
                state_machine.SendSMS(message)
            print_and_log("მითითებულ ნომერზე '{}' sms-ი წარმატებით გაიგზავნა gammu-თი.".format(number))
        except Exception as ex:
            print_and_log("შეცდომა sms გაგზავნისას. Phone number = {}. Exception = {}".format(number, ex))
            failed_numbers.append(number)

    print_and_log('დასრულდა gammu-თი sms-ების დაგზავნა')
    return failed_numbers

def send_sms_via_smsoffice(message='', numbers='', numbers_file_path='', send_all_together=True, timeout=3, try_number=3, time_until_next_try=2):
    numbers = read_numbers(numbers)
    if not numbers:
        numbers = read_numbers_from_file(numbers_file_path)

    smsoffice_error_codes = { 0: "მესიჯი მიღებულია smsoffice -ს მიერ სამომავლოდ ნომერთან გადასაგზავნად",
                             10: "destination შეიცავს არაქართულ ნომრებს",
                             20: "ბალანსი არასაკმარისია",
                             40: "გასაგზავნი ტექსტი 160 სიმბოლოზე მეტია",
                             60: "ბრძანებას აკლია content პარამეტრის მნიშვნელობა, გასაგზავნი ტექსტი",
                             70: "ბრძანებას აკლია ნომრები",
                             75: "ყველა ნომერი სტოპ სიაშია",
                             76: "ყველა ნომერი არასწორი ფორმატითაა მოწოდებული",
                             77: "ყველა ნომერი სტოპ სიაშია ან არასწორი ფორმატითაა მოწოდებული",
                             80: "key -ს შესაბამისი მომხმარებელი ვერ მოიძებნა",
                             110: "sender პარამეტრის მნიშვნელობა გაუგებარია",
                             120: "გააქტიურეთ api -ის გამოყენების უფლება პროფილის გვერდზე",
                             150: "sender არ იძებნება სისტემაში. შეამოწმეთ მართლწერა",
                             500: "ბრძანებას აკლია key პარამეტრი",
                             600: "ბრძანებას აკლია destination პარამეტრი",
                             700: "ბრძანებას აკლია sender პარამეტრი",
                             800: "ბრძანებას აკლია content პარამეტრი",
                            -100: "დროებითი შეფერხება",
                           }

    failed_numbers = []
    print_and_log('იწყება smsoffice-ით sms-ების დაგზავნა')
    for try_index in range(1, try_number + 1):
        for number in numbers:
            params = {'key': sms_offic_key,
                      'destination': number,
                      'sender': 'IES',
                      'content': message
                     }
            try:
                response = requests.post(sms_offic_url, timeout=timeout, params=params)
                if not response.ok:
                    failed_numbers.append(number)
                    print_and_log("მითითებულ ნომერზე '{}' ვერ გაიგზავნა sms-ი smsoffice-ით. status_code = '{}', try_index = {}".format(number, response.status_code, try_index))
                    continue
                else:
                    response_json = response.json()
                    response_error_code = int(response_json["ErrorCode"])
                    if response_json["Success"]:
                        if response_error_code == 0:
                            print_and_log("მითითებულ ნომერზე '{}', {}, try_index = {}".format(number, str(smsoffice_error_codes[response_error_code]), try_index))
                        else:
                            print_and_log("მითითებულ ნომერზე '{}', response = '{}', try_index = {}".format(number, str(response_json), try_index))
                    else:
                        failed_numbers.append(number)
                        if response_error_code in smsoffice_error_codes:
                            print_and_log("მითითებულ ნომერზე'{}' ვერ გაიგზავნა sms-ი smsoffice-ით. response = '{}', try_index = {}".format(number, str(smsoffice_error_codes[response_error_code]), try_index))
                            continue
                        else:
                            print_and_log("მითითებულ ნომერზე'{}' ვერ გაიგზავნა sms-ი smsoffice-ით. response = '{}', try_index = {}.".format(number, str(response_json), try_index))
            
            except Exception as ex:
                failed_numbers.append(number)
                print_and_log("მითითებულ ნომერზე'{}' ვერ გაიგზავნა sms-ი smsoffice-ით. try_index = {}.\n{} ".format(number,  try_index, str(ex)))
        
        if not failed_numbers:
            print_and_log("ყველა ნომერთან sms-ები დაიგზავნა წარმატებით smsoffice-ით. try_index = {}".format(try_index))
            break
        else:
            print_and_log("sms-ების დაგზავნა smsoffice-ით ვერ მოხერხდა {} ნომერთან. try_index = {}".format(len(failed_numbers), try_index))

            numbers = list(failed_numbers)
            if try_index != try_number:
                failed_numbers = []
                time.sleep(time_until_next_try)
    print_and_log('დასრულდა smsoffice-ით sms-ების დაგზავნა')
    return failed_numbers

def check_smsoffice_balance():
    smsoffice_balance_warning_list_path = script_path + '/smsoffice_balance_warning_list'
    smsoffice_balance_pickle_path = script_path + '/smsoffice_balance_check_time.pickle'
    current_time = datetime.datetime.now()
    print_and_log('იწყება smsoffice-ის ბალანსის შემოწმება')
    try:
        smsoffice_balance_response = requests.get(smsoffice_balance_url)
        smsoffice_balance = smsoffice_balance_response.json()

        if smsoffice_balance <= smsoffice_balance_min_warning_value:
            balance_warn_message = "smsoffice-ის ბალანსი იწურება. დარჩენილია {} sms-ი".format(str(smsoffice_balance))   
            if os.path.exists(smsoffice_balance_pickle_path):
                try:
                    with open(smsoffice_balance_pickle_path, 'rb') as file:
                        last_check_time = pickle.load(file)
                        time_diff_delta = current_time - last_check_time
                        time_diff_hours = time_diff_delta.total_seconds() / 3600 
    
                        if time_diff_hours > smsoffice_balance_check_time_interval:
                            with open(smsoffice_balance_pickle_path, 'wb') as file:
                                pickle.dump(current_time, file)
                            send_sms(message=balance_warn_message, numbers='', numbers_file_path=smsoffice_balance_warning_list_path, use_gsm_modem=False, use_magti=False, use_smsoffice=True)
                            print_and_log("დაიგზავნა შეტყობინებები smsoffice-ის ბალანსის ამოწურვის შესახებ")
                except Exception as ex:
                    print_and_log("შეცდომა pickle load-ის ჩატვირთვისას. Exception = {}".format(str(ex)))
            else:
                try:
                    with open(smsoffice_balance_pickle_path, 'wb') as file:
                        pickle.dump(current_time, file)
                    send_sms(message=balance_warn_message, numbers='', numbers_file_path=smsoffice_balance_warning_list_path, use_gsm_modem=False, use_magti=False, use_smsoffice=True)
                    print_and_log("დაიგზავნა შეტყობინებები smsoffice-ის ბალანსის ამოწურვის შესახებ")
                except Exception as ex:
                    print_and_log("შეცდომა pickle load-ის ჩატვირთვისას. Exception = {}".format(str(ex)))

    except Exception as ex:
        print_and_log("შეცდომა smsoffice-ის ბალანსის შემოწმებისას. Exception = {}".format(str(ex)))
    print_and_log('დასრულდა smsoffice-ის ბალანსის შემოწმება')


def send_sms_via_gsm_modem(message='', numbers='', numbers_file_path=''):
    numbers = read_numbers(numbers)
    if not numbers:
        numbers = read_numbers_from_file(numbers_file_path)

    data = {'code': code, 'message': message, 'numbers': ','.join(numbers)}

    print_and_log('იწყება gsm მოდემით  sms - ების დაგზავნა')
    try:
        response = requests.post(ies_gsm_sms_sender_url, data=data)
        if response.ok:
            print_and_log("მითითებულ ნომრებზე '{}' sms გაიგზავნა  წარმატებით gsm მოდემით".format(numbers))
        else:
            print_and_log('შეცდომა gsm მოდემთან დაკავშირებისას {}'.format(response.text))
    except Exception as ex:
        print_and_log('შეცდომა gsm მოდემთან დაკავშირებისას {}'.format(str(ex)))

    print_and_log('დასრულდა gsm მოდემით  sms - ების დაგზავნა')
    
