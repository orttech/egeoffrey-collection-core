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

import os

from sdk.python.module.controller import Controller
import sdk.python.utils.command

class Webserver(Controller):
    # What to do when initializing
    def on_init(self):
        self.gui_env_file = os.path.abspath(os.path.dirname(__file__))+"/html/gui/env.js"
        
    # What to do when running
    def on_start(self):
        self.log_info("Setting up environment...")
        # default gui environment variables can be overridden with EGEOFFREY_GUI_* variables (e.g. EGEOFFREY_GUI_GATEWAY_HOSTNAME will be passed as EGEOFFREY_GATEWAY_HOSTNAME to the gui
        envs = os.environ
        f = open(self.gui_env_file, "a")
        for env in envs:
            if not env.startswith("EGEOFFREY_GUI_"): continue
            gui_env = env.replace("_GUI", "")
            value = envs[env]
            try: 
                int(value)
                value = int(value)
            except ValueError:
                value = '"'+str(value)+'"'
            f.write("\nwindow."+gui_env+" = "+str(value))
        f.close()
        self.log_info("Starting webserver...")
        self.log_debug(sdk.python.utils.command.run("cp -f setup/nginx.conf /etc/nginx/conf.d/default.conf"))
        self.log_debug(sdk.python.utils.command.run("killall nginx >/dev/null 2>&1"))
        self.log_debug(sdk.python.utils.command.run("nginx -c /etc/nginx/nginx.conf"))
        
    # What to do when shutting down
    def on_stop(self):
        self.log_info("Stopping webserver...")
        self.log_debug(sdk.python.utils.command.run("killall nginx >/dev/null 2>&1"))
        
    # What to do when receiving a request for this module    
    def on_message(self, message):
        pass
        
     # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self, message):
        pass