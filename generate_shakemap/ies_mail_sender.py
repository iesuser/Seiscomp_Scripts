# -*- coding: utf-8 -*-
from email import encoders
from email.mime.base import MIMEBase
import io
import base64
import pickle
import os

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def gmail_authenticate():
    creds = None

    # აბსოლუტური ბილიკები ამ ფაილის მდებარეობიდან
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, 'credentials/token.pickle')
    credentials_path = os.path.join(base_dir, 'credentials/credentials.json')

    # Token ფაილის წაკითხვა
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token_file:
            creds = pickle.load(token_file)

    # თუ token არ არის ან არასწორია
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_console()  # არ მოითხოვს ბრაუზერს/headless friendly
        with open(token_path, 'wb') as token_file:
            pickle.dump(creds, token_file)

    return build('gmail', 'v1', credentials=creds)


# მითითებული filename ფაილიდან ფუნქცია კითხულობს სახელ გვარს და ელფოსტას და აბრუნებს list ების სახით
# ქვემოთ ნაჩვენებია მაგალითი თუ როგორი შეიძლება იყოს filename ფაილი:
def get_contacts(filename): 
    fullnames = []
    emails = []
    with io.open(filename, mode='r', encoding='utf-8') as contacts_file:
        for a_contact in contacts_file:
            splited_line = a_contact.strip().split()
            fullnames.append(splited_line[0] + ' ' + splited_line[1])
            emails.append(splited_line[2])
    return fullnames, emails


# ფუნქცია ფაილიდან კითხულობს ელფოსტის მისამართებს
# ქვემოთ ნაჩვენებია მაგალითი თუ როგორი შეიძლება იყოს filename ფაილი:
def get_emails(filename):
    emails = []
    with io.open(filename, mode='r', encoding='utf-8') as contacts_file:
        for a_contact in contacts_file:
            emails.append(a_contact.strip())
    return emails

# ელფოსტის გასაგზავნი ფუნქცია
# emails პარამეტრი შეიძლება იყოს ფაილის მისამართი სადაც ყოველი ახალი ხაზი არის საკონტაქტო ელფოსტა ან ელფოსტების list ები
def send_mail(emails, subject, message, email_type='plain', attachments=None):
    if isinstance(emails, str):
        emails = get_emails(emails)

    service = gmail_authenticate()
    for to_email in emails:
        msg = MIMEMultipart()
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, email_type))
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        attachment = MIMEBase('application', 'octet-stream')
                        attachment.set_payload(f.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                    msg.attach(attachment)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        try:
            sent = service.users().messages().send(userId="me", body={'raw': raw}).execute()
            # print(f"Email sent to {to_email} | Message ID: {sent['id']}")
        except Exception as e:
            print(f"Failed to send to {to_email}: {e}")




def main():
    # mail_list_filename = str(sys.argv[1])
    # send_mail('./mail_list', "წერილი გამოგზაცნილია mail_sender.py სკრიპტიდან", "სატესტო წერილი")
    # send_mail(['roma.grigalashvili@iliauni.edu.ge'], "წერილი გამოგზაცნილია mail_sender.py სკრიპტიდან", "სატესტო წერილი")
    print("done")


if __name__ == '__main__':
    main()
