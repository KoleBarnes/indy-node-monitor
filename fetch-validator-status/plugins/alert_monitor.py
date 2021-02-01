import plugin_collection
#from .google_sheets import gspread_authZ, gspread_append_sheet
import datetime
import argparse
import os
import logging

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
            print(result)
            if result: logging.warning(result)
            # Put CSV to store nodes that are down, for how long and if they have been notified at given times (2 hours, 24 hours)
            # CSV to store email creds. Use tokens for email password if possible. 
        
        else:
            print(self.description, 'not used skipping.')

    def notify(self):
        pass