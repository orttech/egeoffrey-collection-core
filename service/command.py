### service/command: run system commands, useful to e.g. interact with a utility which communicates with a sensor
## HOW IT WORKS: 
## DEPENDENCIES:
# OS: 
# Python: 
## CONFIGURATION:
# required: 
# optional: 
## COMMUNICATION:
# INBOUND: 
# - IN: 
#   required: command
#   optional: 
# OUTBOUND: 

import json
import datetime
import time
 
from sdk.python.module.service import Service

import sdk.python.utils.command

class Command(Service):
    # What to do when initializing
    def on_init(self):
        pass
    
    # What to do when running
    def on_start(self):
        pass
    
    # What to do when shutting down    
    def on_stop(self):
        pass

    def run_command(self, command):
        self.log_debug("Executing command "+command)
        return sdk.python.utils.command.run(command)

    # What to do when receiving a request for this module        
    def on_message(self, message):
        # poll the sensor
        if message.command == "IN":
            if not self.is_valid_configuration(["command"], message.get_data()): return
            sensor_id = message.args
            command = message.get("command")
            # reply to the requesting module 
            message.reply()
            message.set("value", self.run_command(command))
            # send the response back
            self.send(message)
        # run as an actuator
        elif message.command == "OUT":
            if not self.is_valid_configuration(["command"], message.get_data()): return
            command = message.get("command")
            self.run_command(command)
        
    # What to do when receiving a new/updated configuration for this module
    def on_configuration(self,message):
        # register/unregister the sensor
        if message.args.startswith("sensors/"):
            if message.is_null: 
                sensor_id = self.unregister_sensor(message)
            else: 
                sensor_id = self.register_sensor(message)
                
