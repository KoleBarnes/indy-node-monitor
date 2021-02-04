import plugin_collection
#from .google_sheets import gspread_authZ, gspread_append_sheet
import datetime
import argparse
import os
import logging
import json
import smtplib
from email.message import EmailMessage
import codecs

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
            logging.basicConfig(filename='./logs/alerts.log', datefmt='%m/%d/%Y %I:%M:%S %p', format='%(asctime)s: %(levelname)s: %(message)s', level=logging.DEBUG)
            filtered_result = []
            for item in result:
                if ("info" in item["status"]) or ("warnings" in  item["status"]) or ("errors" in  item["status"]):
                    filtered_result.append(item)
            result = filtered_result
            
            #print(result)
            print(json.dumps(result, indent=2))
            
            if result: 
                for node in result:
                    #logging.warning(json.dumps(result, indent=2))
                    self.notify(node["name"], network_name)
            # Put CSV to store nodes that are down, for how long and if they have been notified at given times (2 hours, 24 hours)
        
        else:
            print(self.description, 'not used skipping.')

    def notify(self, node, network_name):
        EMAIL_ADDRESS = os.environ.get('Sovrin_Email_App_User')
        EMAIL_PASSWORD = os.environ.get('Sorvin_Email_App_Pwd')
        EMAIL_RECIPIENT = [EMAIL_ADDRESS]

        msg = EmailMessage()
        msg['Subject'] = f'Your node ({node}) on the {network_name} needs attention'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_RECIPIENT
        
        msg.set_content('This is a plan text email')

        html = codecs.open("./plugins/alerts/downedNode.html", "r", "utf-8")
        html = html.read()

        msg.add_alternative(html, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print('Email Sent!')

        pass