'''
Git Hub Repo: https://github.com/gdiepen/python_plugin_example
'''

import plugin_collection
#from .google_sheets import gspread_authZ, gspread_append_sheet
import datetime

class sovrin_network_metrics(plugin_collection.Plugin):
    
    def __init__(self):
        super().__init__()
        self.description = 'Sovrin Network Metrics Function'

    def perform_operation(self, result, network_name, metrics_log_info):
        gauth_json = metrics_log_info[0]
        file_name = metrics_log_info[1]
        worksheet_name = metrics_log_info[2]

        #authD_client = gspread_authZ(gauth_json)
        
        message = ""
        num_of_nodes = 0
        nodes_offline = 0
        time = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S') # formated to 12/3/2020 21:27:49

        for node in result:
            num_of_nodes += 1
            if node["status"]["ok"] == False:
                nodes_offline += 1

        networkResilience = num_of_nodes - round((num_of_nodes - 1 ) / 3)

        # Could have a stepped warning system
        if nodes_offline >= networkResilience:
            message = "Network Resilience Danger!"

        active_nodes = num_of_nodes - nodes_offline

        row = [time, network_name, num_of_nodes, nodes_offline, networkResilience, active_nodes, message]
        print(row)
        # gspread_append_sheet(authD_client, file_name, worksheet_name, row)
        print("\033[1;92;40mPosted to " + file_name + " in sheet " + worksheet_name + ".\033[m")

        return row