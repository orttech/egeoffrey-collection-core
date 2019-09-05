### send out sms notifications (betamax voip service)
## HOW IT WORKS: 
## DEPENDENCIES:
# OS:
# Python: 
## CONFIGURATION:
# required: "hostname", "ssl", "username", "password", "from", "to"
# optional: 
## COMMUNICATION:
# INBOUND: 
# - NOTIFY: receive a notification request
# OUTBOUND: 

from sdk.python.module.notification import Notification

import sdk.python.utils.web
import sdk.python.utils.exceptions as exception

class Betamax_sms(Notification):
    # What to do when initializing
    def on_init(self):
        # constants
        self.max_retries = 3
        # configuration settings
        self.house = {}
        # require configuration before starting up
        self.config_schema = 1
        self.add_configuration_listener("house", 1, True)
        self.add_configuration_listener(self.fullname, "+", True)

    # What to do when running
    def on_start(self):
        pass
        
    # What to do when shutting down
    def on_stop(self):
        pass
        
    # send the message
    def send_sms(self, to, text):
        protocol = "https://" if self.config["ssl"] else "http://"
        url = protocol+self.config["hostname"]+"/myaccount/sendsms.php?username="+self.config["username"]+"&password="+self.config["password"]+"&from="+str(self.config["from"])+"&to="+str(to)+"&text="+text
        try: 
            response = sdk.python.utils.web.get(url)
        except Exception,e:
            self.log_warning("unable to connect to the sms module: "+exception.get(e))
            return False
        if "<resultstring>success</resultstring>" in response: return True
        return False

    # What to do when ask to notify
    def on_notify(self, severity, text):
        text = "["+self.house["name"]+"] "+text
        for to in self.config["to"].split(","):
            retries = self.max_retries
            while retries > 0 :
                result = self.send_sms(to, text)
                if result: 
                    self.log_info("Sent SMS to "+str(to)+" with text: "+text)
                    retries = 0
                else: 
                    self.log_error("Failed #"+str(retries)+" to send SMS to "+str(to)+" with text: "+text)
                    retries = retries - 1

     # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self, message):
        if message.args == "house" and not message.is_null:
            if not self.is_valid_configuration(["name"], message.get_data()): return False
            self.house = message.get_data()
        # module's configuration
        if message.args == self.fullname and not message.is_null:
            if message.config_schema != self.config_schema: 
                return False
            if not self.is_valid_configuration(["hostname", "ssl", "username", "password", "from", "to"], message.get_data()): return False
            self.config = message.get_data()