### controller/webserver: runs the webserver for serving static gui contents
## HOW IT WORKS: 
## DEPENDENCIES:
# OS: nginx
# Python: 
## CONFIGURATION:
# required: 
# optional: 
## COMMUNICATION:
# INBOUND: 
# OUTBOUND: 

from sdk.python.module.controller import Controller
import sdk.python.utils.command

class Webserver(Controller):
    # What to do when initializing
    def on_init(self):
        pass
        
    # What to do when running
    def on_start(self):
        self.log_info("Starting webserver...")
        self.log_debug(sdk.python.utils.command.run("cp -f setup/nginx.conf /etc/nginx/conf.d/default.conf"))
        self.log_debug(sdk.python.utils.command.run("killall nginx"))
        self.log_debug(sdk.python.utils.command.run("nginx -c /etc/nginx/nginx.conf"))
        
    # What to do when shutting down
    def on_stop(self):
        self.log_info("Stopping webserver...")
        self.log_debug(sdk.python.utils.command.run("killall nginx"))
        
    # What to do when receiving a request for this module    
    def on_message(self, message):
        pass
        
     # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self, message):
        pass