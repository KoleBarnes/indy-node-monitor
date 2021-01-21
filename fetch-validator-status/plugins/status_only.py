import plugin_collection
import json

class main(plugin_collection.Plugin):
    
    def __init__(self, status_only: bool = False):
        super().__init__()
        self.index = 2
        self.name = 'status_only'
        self.description = ''
        self.type = ''
        self.status_only = status_only

    def parse_args(self, parser, argv=None, status_only: bool = False):
        parser.add_argument("--status", action="store_true", help="Get status only.  Suppresses detailed results.")
        args, unknown = parser.parse_known_args(argv)

        self.status_only = args.status
    
    def perform_operation(self, result, network_name):
        if self.status_only:
            for node in result:
                del node["response"]
            print(json.dumps(result, indent=2))
