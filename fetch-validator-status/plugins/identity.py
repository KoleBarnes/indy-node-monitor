import plugin_collection 

class Identity(plugin_collection.Plugin):
    """This plugin is just the identity function: it returns the argument
    """
    def __init__(self):
        super().__init__()
        self.description = 'Identity function'

    def perform_operation(self, result, network_name, metrics_log_info):
        """The actual implementation of the identity plugin is to just return the
        argument
        """
        print("Made it to Identity")

        return