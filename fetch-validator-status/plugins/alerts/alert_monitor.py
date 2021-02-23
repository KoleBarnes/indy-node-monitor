import plugin_collection
import datetime
import argparse
import os
import json
import smtplib
from email.message import EmailMessage
import requests

class main(plugin_collection.Plugin):
    
    def __init__(self,  alerts_only = None):
        super().__init__()
        self.index = 2
        self.name = 'Alerts'
        self.description = ''
        self.type = ''
        self.alerts_only = alerts_only

    # def description(self)
    #     return self.description


    def parse_args(self, parser, argv=None):
        parser.add_argument("--alerts", action="store_true", help="Filter results based on alerts.  Only return data for nodes containing detected 'info', 'warnings', or 'errors'.")

        args, unknown = parser.parse_known_args(argv)

        if args.alerts:
            self.alerts_only = args.alerts

    def perform_operation(self, result, network_name):
        # Filter on alerts
        if self.alerts_only:
            filtered_result = []
            for item in result:
                if ("info" in item["status"]) or ("warnings" in  item["status"]) or ("errors" in  item["status"]):
                    filtered_result.append(item)
            result = filtered_result

            # print(json.dumps(result, indent=2))

            if result: 
                for node in result:

                    ''' 
                    - Archive alert files when there aren't alerts/alerts have been resolved
                    
                    - get rid of email sent and use time sent if its not null then the was sent
                    
                    - Take out Email content from there individual files and just have them all in one file

                    - call all stages feilds steps in the json file

                    - pop node from the data pulled from the json file once the data has been colected then use
                      time till email to sort the steps with (key=lambda x: x.index, reverse=False) then
                      go throught the steps to see when and if an email is to be sent.
                    '''

                    node_name = node["name"]
                    alert_log_path = "./plugins/alerts/AlertLogs/"
                    ALL_EMAILS_SENT = False

                    # If Alert already exist work with it; else create an Alert
                    if os.path.exists(f'{alert_log_path}{node_name}.json'):

                        # Get Alert Json Content
                        with open(f'{alert_log_path}{node_name}.json', 'r') as json_file:
                            data = json.load(json_file)

                        # Go throught the stages of the alert (skipping node info) untill a stage with email_sent = False, then get the contents from that stage and send email.
                        object_count = 0
                        for thing in data:
                            object_count += 1
                            if thing != 'node':
                                if not data[thing]["time_sent"]:
                                    stage = thing
                                    epoch_time = int(data["node"]["status"]["timestamp"])
                                    time_till_email = data[thing]["time_till_email"]
                                    html_content = data[thing]["HTML_content"]
                                    plainText_content = data[thing]["plainText_content"]
                                    recipients_email = data[thing]["recipients_email"]
                                    cc_email = data[thing]["cc_email"]
                                    break
                                # If all emails have been sent; stop. 
                                elif object_count == len(data):
                                    ALL_EMAILS_SENT = True

                        if not ALL_EMAILS_SENT:
                            # Convert epoch time from node and the current time
                            node_timestamp = datetime.datetime.fromtimestamp(epoch_time)
                            time_now = datetime.datetime.now()

                            # Calculate the differents in time in minutes.
                            time_delta = (time_now - node_timestamp)
                            total_seconds = time_delta.total_seconds()
                            minutes = total_seconds/60

                            # Find out if it is time to send an email based on time from the stage the alert is in. 
                            # StageOne: 2 hours/120 minutes. StageTwo: 24 hours/1440 minutes. StageThree: 48 Hours/2880 minutes.
                            if minutes >= time_till_email:
                                # Send email
                                email_sent = self.notify(node_name, network_name, recipients_email, cc_email, html_content, plainText_content)
                                if email_sent:
                                    # Open and update the Alert with the current time and that the email was sent in order to increase the stage the alerts is in.
                                    data[stage]["email_sent"] = email_sent
                                    data[stage]["time_sent"] = str(datetime.datetime.now().strftime('%s'))
                                    with open(f'{alert_log_path}{node_name}.json', 'w') as json_file:
                                        data.update(data)
                                        json_file.seek(0)
                                        json.dump(data, json_file, indent=2)
                                    print(f'{stage} email Sent to {node_name} on network {network_name}!') 

                            # States when the next email will be sent for the next stage.
                            elif minutes < time_till_email:
                                email_eta = time_till_email - minutes
                                print(f'{stage} Email will be sent in {email_eta} to {node_name} on network {network_name} if not resolved.')

                        else:
                            print(f'All emails have been sent to {node_name}.')

                    # Create a file for the new alert if there isn't one.
                    else:
                        recipients_email = self.get_contact_info(node_name)
                        self.create_alert_log(node, node_name, alert_log_path, recipients_email)
                        

    def notify(self, node, network_name, recipients_email, cc_email, html_content, plainText_content):
        EMAIL_ADDRESS = os.environ.get('Sovrin_Email_App_User')
        EMAIL_PASSWORD = os.environ.get('Sorvin_Email_App_Pwd')
        EMAIL_RECIPIENT = None
        EMAIL_CC = cc_email

        # Find out what network we are on and find which folder the log will be in.
        if network_name == 'Sovrin Main Net':
            log_folder = 'live'
        elif network_name == 'Sovrin Staging Net':
            log_folder = 'sandbox'
        elif network_name == 'Sovrin Builder Net':
            log_folder = 'net3'

        msg = EmailMessage()
        msg['Subject'] = f'Your node ({node}) on the {network_name} needs attention'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_RECIPIENT
        msg['Cc'] = EMAIL_CC

        # Email will send a HTML and plain text options for email clients that don't support HTML format.

        # Plain Text Option #
        content = open(plainText_content).read().format(node=node, network_name=network_name, log_folder=log_folder, recipients_email=recipients_email)
        msg.set_content(content)

        # HTML Option #
        html = open(html_content).read().format(node=node, network_name=network_name, log_folder=log_folder, recipients_email=recipients_email)
        msg.add_alternative(html, subtype='html')

        # Send Email with contents and return if the email was sent.
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            email_sent = True
        
        return email_sent


    def get_contact_info(self, node_name):

        AIRTABLE_API_KEY = os.environ.get('Airtable_API_Key')
        headers = {"Authorization": "Bearer " + AIRTABLE_API_KEY}

        companies_url = "https://api.airtable.com/v0/appq6dtcBJNmgbmCt/Companies/"
        contacts_url = "https://api.airtable.com/v0/appq6dtcBJNmgbmCt/Contacts/"

        # Gets the company name by filtering for the alerted node listed with the company from airtable.
        companies_url = companies_url + f'?filterByFormula=%7BSteward Nodes%7D="{node_name}"'
        response = requests.get(companies_url, headers=headers)
        airtable_response = response.json()
        # print(json.dumps(airtable_response, indent=2))
        airtable_records = airtable_response["records"]
        for record in airtable_records:
            if "Company Name" in record["fields"]:
                company_name = record["fields"]["Company Name"]
                # print(company_name)
        
        # Filters and gets the technical contacts associated with the company from airtable.
        contacts_url = contacts_url + f'?filterByFormula=AND(Company="{company_name}", SEARCH("Technical",%7BContact Type copy%7D))'
        response = requests.get(contacts_url, headers=headers)
        airtable_response = response.json()
        # print(json.dumps(airtable_response, indent=2))
        airtable_records = airtable_response["records"]
        for record in airtable_records:
            if "Email" in record["fields"]: Email = record["fields"]["Email"]
            # print(f"Email: {Email}\n")

        return(Email)

    def create_alert_log(self, node, node_name, alert_log_path, recipients_email):
        print('New alert creating log...')

        email_content_path = "./plugins/alerts/EmailContent/"
        recipients_email = [recipients_email]
        cc_email = ["kole@sovrin.org"]

        alert = {
            "node": node,
            "stageOne": {"time_sent": None, "time_till_email": 120, "HTML_content": email_content_path + "StageOne/StageOneEmail.html", "plainText_content": email_content_path + "StageOne/StageOneEmail.txt", "recipients_email": recipients_email, 'cc_email': cc_email},
            "stageTwo": {"time_sent": None, "time_till_email": 1440, "HTML_content": email_content_path + "StageTwo/StageTwoEmail.html", "plainText_content": email_content_path + "StageTwo/StageTwoEmail.txt", "recipients_email": recipients_email, 'cc_email': cc_email},
            "stageThree": {"time_sent": None, "time_till_email": 2880, "HTML_content": email_content_path + "StageThree/StageThreeEmail.html", "plainText_content": email_content_path + "StageThree/StageThreeEmail.txt", "recipients_email": recipients_email, 'cc_email': cc_email}
        }

        # Create Alert file with dict above.
        with open(f'{alert_log_path}{node_name}.json', 'w') as outfile:
            json.dump(alert, outfile, indent=2)
            print('Log created.')