import plugin_collection
import argparse
import json

class main(plugin_collection.Plugin):
    
    def __init__(self,  alerts = None):
        super().__init__()
        self.index = 2
        self.name = 'Alerts'
        self.description = ''
        self.type = ''
        self.alerts = alerts

    # def description(self)
    #     return self.description

    def parse_args(self, parser, argv=None):
        parser.add_argument("--alerts", action="store_true", help="Filter results based on alerts.  Only return data for nodes containing detected 'info', 'warnings', or 'errors'.")

    def load_parse_args(self, args):
        global verbose
        verbose = args.verbose

        if args.alerts:
            self.alerts = args.alerts

    def perform_operation(self, result, network_name):
        # Filter on alerts
        if self.alerts:
            filtered_result = []
            for item in result:
                if ("info" in item["status"]) or ("warnings" in  item["status"]) or ("errors" in  item["status"]):
                    filtered_result.append(item)
            result = filtered_result
            print(json.dumps(result, indent=2))

