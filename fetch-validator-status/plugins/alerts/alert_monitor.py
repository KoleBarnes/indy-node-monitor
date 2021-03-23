import plugin_collection
import datetime
import argparse
import os
import json
import logging
import smtplib
import requests
from email.message import EmailMessage

class main(plugin_collection.Plugin):
    
    def __init__(self):
        super().__init__()
        self.index = 2
        self.name = 'alerts_monitor'
        self.description = ''
        self.type = ''

    def parse_args(self, parser):
        parser.add_argument("--alerts_monitor", action="store_true", help="Filter results based on alerts.  Only return data for nodes containing detected 'info', 'warnings', or 'errors'.")
        parser.add_argument("--notify", action="store_true", help="Send email notifications of alerts.")


    def load_parse_args(self, args):
        global verbose
        verbose = args.verbose

        self.enabled = args.alerts_monitor

        if args.notify:
            self.notify = args.notify

    async def perform_operation(self, result, network_name, response, verifiers):
        # Filter on alerts
        filtered_result = []
        for item in result:
            if ("info" in item["status"]) or ("warnings" in  item["status"]) or ("errors" in  item["status"]):
                filtered_result.append(item)
        result = filtered_result
            
        if result:
            if self.notify: 
                for node in result:
                    node_name = node["name"]
                    alert_log_path = "./plugins/alerts/AlertLogs/"
                    logging.basicConfig(filename='./plugins/alerts/Debug.log', datefmt='%m/%d/%Y %I:%M:%S %p', format='%(asctime)s: %(levelname)s: %(message)s', level=logging.DEBUG)

                    if os.path.exists(f'{alert_log_path}{node_name}.json'):
                        self.read_alert_log(node_name, alert_log_path, network_name)
                    else:
                        try:
                            logging.info(f'Getting data for {node_name} on {network_name}')
                            recipients_email = self.get_contact_info(node_name)
                        except Exception as e: 
                            logging.error(e)
                            print("\033[91mError occurred while getting info from Airtable. Check debug log!\033[m")
                            EMAIL_ADDRESS = os.environ.get('Sovrin_Email_App_User')
                            subject = "Error occurred in Alerts in Node Monitor"
                            content = open('./plugins/alerts/EmailContent/ErrorAlert.txt').read()
                            self.send_email(subject, content, node_name, network_name, cc_email=EMAIL_ADDRESS)
                        else:
                            self.create_alert_log(node, node_name, network_name, alert_log_path, recipients_email)
                            self.read_alert_log(node_name, alert_log_path, network_name)
            
            else:
                print(json.dumps(result, indent=2))

        return result

                        
    def get_contact_info(self, node_name):
        AIRTABLE_API_KEY = os.environ.get('Airtable_API_Key')
        headers = {"Authorization": "Bearer " + AIRTABLE_API_KEY}

        COMPANIES_URL = os.environ.get('Airtable_Companies_URL')
        CONTACTS_URL = os.environ.get('Airtable_Contacts_URL')
        CONTACT_TYPE = "Technical"

        # Gets the company name by filtering for the alerted node listed with the company from airtable.
        COMPANIES_URL = COMPANIES_URL + f'?filterByFormula=SEARCH("{node_name}",%7BSteward Nodes%7D)'
        company_records = self.get_records(COMPANIES_URL, headers)

        company_name = None
        for record in company_records["records"]:
            company_name = record["fields"].get("Company Name")
            if not company_name:
                logging.debug(company_records)
                raise Exception("Could not get company name!")

        # Filters and gets the technical contacts associated with the company from airtable.
        CONTACTS_URL = CONTACTS_URL + f'?filterByFormula=AND(Company="{company_name}", SEARCH("{CONTACT_TYPE}",%7BContact Type%7D))'
        contact_records = self.get_records(CONTACTS_URL, headers)

        contacts_email = []
        for record in contact_records["records"]:
            contacts_email.append(record["fields"].get("Email"))

        if not contacts_email:
            raise Exception(f'No "{CONTACT_TYPE}" records found!')

        contacts = {
            "Company Name": company_name,
            "Email": contacts_email
        }
        # print(json.dumps(contacts, indent=2))

        return(contacts)

    def get_records(self, url, headers):
        response = requests.get(url, headers=headers)
        airtable_response = response.json()
        # print(json.dumps(airtable_response, indent=2))
        has_items = bool(airtable_response["records"])
        if not has_items:
            logging.error("Airtable responded with empty response!")
        return(airtable_response)

    def create_alert_log(self, node, node_name, network_name, alert_log_path, recipients_email):
        print('New alert creating log...', end='')
        email_content_path = "./plugins/alerts/EmailContent/"
        recipients_email = [recipients_email]
        cc_email = [os.environ.get('Sovrin_Email_App_User')]

        alert = {
            "network": network_name,
            "node": node,
            "contactInfo": {"recipients_email": recipients_email, 'cc_email': cc_email},
            "notify": {
                "1": {"time_sent": None, "time_till_email": 120, "plainText_content": email_content_path + "StageOneEmail.txt"},
                "2": {"time_sent": None, "time_till_email": 1440, "plainText_content": email_content_path + "StageTwoEmail.txt"},
                "3": {"time_sent": None, "time_till_email": 2880, "plainText_content": email_content_path + "StageThreeEmail.txt"}
            }
        }

        # Create Alert file with dict above.
        with open(f'{alert_log_path}{node_name}.json', 'w') as outfile:
            json.dump(alert, outfile, indent=2)
            print('\033[92mDONE\033[m')

    def read_alert_log(self, node_name, alert_log_path, network_name):
        ALL_EMAILS_SENT = False

        # Get Alert Json Content
        with open(f'{alert_log_path}{node_name}.json', 'r') as json_file:
            data = json.load(json_file)

        # Go throught the stages of the alert until a stage with time_sent = Null, then get info.
        num_stages = data["notify"]
        for stage in num_stages:
            if not data["notify"][stage]["time_sent"]:
                epoch_time = int(data["node"]["status"].get("timestamp"))
                recipients_email = data["contactInfo"].get("recipients_email")
                cc_email = data["contactInfo"].get("cc_email")
                time_till_email = data["notify"][stage].get("time_till_email")
                plainText_content = data["notify"][stage].get("plainText_content")
                break
        # If all emails have been sent; stop. 
        else:
            ALL_EMAILS_SENT = True

        if not ALL_EMAILS_SENT:
            node_timestamp = datetime.datetime.fromtimestamp(epoch_time)
            time_now = datetime.datetime.now()
            time_delta = (time_now - node_timestamp)
            total_seconds = time_delta.total_seconds()
            minutes = total_seconds/60

            # Find out if it is time to send an email based on the time from the stage the alert is in. 
            # 1: 2 hours/120 minutes. 2: 24 hours/1440 minutes. 3: 48 Hours/2880 minutes.
            if minutes >= time_till_email:
                # Build email
                
                # Find out what network we are on and find which folder the log will be in.
                if network_name == 'Sovrin Main Net': log_folder = 'live'
                elif network_name == 'Sovrin Staging Net': log_folder = 'sandbox'
                elif network_name == 'Sovrin Builder Net': log_folder = 'net3'

                subject = f'Your node ({node_name}) on the {network_name} needs attention'
                content = open(plainText_content).read().format(node=node_name, network_name=network_name, log_folder=log_folder, recipients_email=recipients_email)

                # Send Email
                email_sent = self.send_email(subject, content, node_name, network_name, recipients_email=recipients_email, cc_email=cc_email)
                if email_sent:
                    # Open and update the alert with the time the email was sent.
                    data["notify"][stage]["time_sent"] = str(datetime.datetime.now().strftime('%s'))
                    with open(f'{alert_log_path}{node_name}.json', 'w') as json_file:
                        data.update(data)
                        json_file.seek(0)
                        json.dump(data, json_file, indent=2)
                    print(f'\033[92mEmail {stage} sent to {node_name} ({network_name})!\033[m') 

            # States when the next email will be sent for the next stage.
            elif minutes < time_till_email:
                email_eta = round(time_till_email - minutes)
                print(f'\033[93mEmail {stage} will be sent in \033[4m{email_eta} minutes\033[m\033[93m to {node_name} ({network_name}) if not resolved.\033[m')

        else:
            print(f'\033[91mAll emails have been sent to {node_name}.\033[m')

    def send_email(self, subject, content, node_name, network_name, recipients_email: str = None, cc_email: str = None):
        EMAIL_ADDRESS = os.environ.get('Sovrin_Email_App_User')
        EMAIL_PASSWORD = os.environ.get('Sorvin_Email_App_Pwd')
        EMAIL_RECIPIENT = None

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_RECIPIENT
        msg['Cc'] = cc_email

        msg.set_content(content)

        # Send Email with contents and return if the email was sent.
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            email_sent = True
        
        return email_sent