import plugin_collection
#from .google_sheets import gspread_authZ, gspread_append_sheet
import datetime
import argparse
import os
import json
import smtplib
from email.message import EmailMessage

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
            
            #print(result)
            print(json.dumps(result, indent=2))
            
            if result: 
                for node in result:

                    '''
                    make a dict with all info needed for the alert ie: was email sent, time email was sent, 
                    what stage of alert that the email was sent at (stage 1: 2hours email to everyone, stage 2: 24hours email to everyone. stage 3: 48hours internal email), 
                    email contents, company email. Before anything gets started.
                    '''

                    if os.path.exists(f'./plugins/alerts/JsonAlertLogs/{node["name"]}.json'):
                        with open(f'./plugins/alerts/JsonAlertLogs/{node["name"]}.json', 'r') as json_file:
                            data = json.load(json_file)
                            epoch_time = int(data["status"]["timestamp"])
                            # epoch_time = 1612728397 # More then 2 hours ago
                        node_timestamp = datetime.datetime.fromtimestamp(epoch_time)
                        time_now = datetime.datetime.now()
                        print(node_timestamp)
                        print(time_now)

                        time_delta = (time_now - node_timestamp)
                        total_seconds = time_delta.total_seconds()
                        minutes = total_seconds/60

                        print(minutes)

                        if minutes >= 120: # and not data["status"]["email_sent"]: # if its been 2 hours and an email has not been sent.
                            email_sent = self.notify(node["name"], network_name) # Send email
                            if email_sent:
                                print(email_sent)
                                with open(f'./plugins/alerts/JsonAlertLogs/{node["name"]}.json', 'w') as json_file:
                                    data["status"]["email_sent"] = email_sent
                                    data.update(data)
                                    json_file.seek(0)
                                    json.dump(data, json_file, indent=2)
                                print(f'Email Sent to {node["name"]} on network {network_name}!') 

                        elif minutes < 120: # and not data["status"]["email_sent"]:
                            email_eta = minutes - 120
                            print(f'Email will be sent in {email_eta} to {node["name"]} on network {network_name} if not resolved.')

                        elif data["status"]["email_sent"]:
                            print(f'Email about node {node["name"]} on network {network_name} already sent.')

                    else:
                        print('New alert creating log...')
                        with open(f'./plugins/alerts/JsonAlertLogs/{node["name"]}.json', 'w') as outfile:
                            json.dump(node, outfile, indent=2)
                            print('Log created.')
        
        else:
            print(self.description, 'not used skipping.')

    def notify(self, node, network_name):
        EMAIL_ADDRESS = os.environ.get('Sovrin_Email_App_User')
        EMAIL_PASSWORD = os.environ.get('Sorvin_Email_App_Pwd')
        EMAIL_RECIPIENT = [EMAIL_ADDRESS]

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

        # Plain Text Option #
        content = open("./plugins/alerts/EmailContentText.txt").read().format(node=node, network_name=network_name, log_folder=log_folder)
        msg.set_content(content)

        # HTML Option #
        # html = open("./plugins/alerts/downedNode.html").read().format(node=node, network_name=network_name)
        # msg.add_alternative(html, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            email_sent = True
        
        return email_sent