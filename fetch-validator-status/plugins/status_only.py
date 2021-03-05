import plugin_collection
import json

class main(plugin_collection.Plugin):
    
    def __init__(self, status_only: bool = False):
        super().__init__()
        self.index = 3 # Set to -1 to disable plug-in.
        self.name = 'Status Only'
        self.description = ''
        self.type = ''
        self.status_only = status_only

    def parse_args(self, parser, argv=None):
        parser.add_argument("--status", action="store_true", help="Get status only.  Suppresses detailed results.")

    def load_parse_args(self, args):
        global verbose
        verbose = args.verbose
        
        self.status_only = args.status
    
    def perform_operation(self, result, network_name):
        if self.status_only:
            for node in result:
                if "response" in node:
                    node.pop("response")
            print(json.dumps(result, indent=2))
