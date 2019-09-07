### service/earthquake: retrieve earthquake information
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
#   required: domain, query
#   optional: 
# OUTBOUND: 

import datetime
import time
import json

from sdk.python.module.service import Service
from sdk.python.utils.datetimeutils import DateTimeUtils

import sdk.python.utils.web
import sdk.python.utils.exceptions as exception

class Earthquake(Service):
    # What to do when initializing
    def on_init(self):
        # constants
        self.limit = 10000
        self.query = "format=text&limit="+str(self.limit)+"&orderby=time-asc"
        # helpers
        self.date = None
        
    # What to do when running
    def on_start(self):
        pass
    
    # What to do when shutting down
    def on_stop(self):
        pass

    # What to do when receiving a request for this module
    def on_message(self, message):
        if message.command == "IN":
            sensor_id = message.args
            # ensure configuration is valid
            if not self.is_valid_configuration(["domain", "query"], message.get_data()): return
            domain = message.get("domain")
            query = message.get("query")
            # if the raw data is cached, take it from there, otherwise request the data and cache it
            cache_key = "/".join([domain])
            if self.cache.find(cache_key): 
                data = self.cache.get(cache_key)
            else:
                # retrieve the data
                try:
                    url = "http://"+domain+"/fdsnws/event/1/query?"+"format=text&limit="+str(self.limit)+"&orderby=time-asc"+"&"+str(query)
                    data = sdk.python.utils.web.get(url)
                except Exception,e: 
                    self.log_warning("unable to connect to "+url+": "+exception.get(e))
                    return
                self.cache.add(cache_key, data) 
            message.reply()
            # load the file
            self.log_debug("parsing data from "+domain+" with "+str(len(data))+" lines")
            # for each line
            for line in data.split("\n"):
                message.clear()
                #EventID|Time|Latitude|Longitude|Depth/Km|Author|Catalog|Contributor|ContributorID|MagType|Magnitude|MagAuthor|EventLocationName
                #    0    1      2          3       4       5     6           7            8           9     10         11           12
                if line.startswith('#'): continue
                # split the entries
                entry = line.split('|')
                if len(entry) != 13: continue
                # set the timestamp to the event's date
                date_format = "%Y-%m-%dT%H:%M:%S.%f"
                date = datetime.datetime.strptime(entry[1], date_format)
                message.set("timestamp", int((date - datetime.datetime(1970, 1, 1)).total_seconds()))
                # prepare the position value
                position = {}
                position["latitude"] = float(entry[2])
                position["longitude"] = float(entry[3])
                position["label"] = str(entry[10])
                date_string = self.date.timestamp2date(self.date.timezone(int(message.get("timestamp"))))
                position["text"] = str(entry[12])
                # prepare the measure
                message.set("value", json.dumps(position))
                # send the response back
                self.send(message)

    # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self,message):
        if message.args == "house" and not message.is_null:
            if not self.is_valid_configuration(["timezone"], message.get_data()): return False
            self.date = DateTimeUtils(message.get("timezone"))
        # register/unregister the sensor
        elif message.args.startswith("sensors/"):
            if message.is_null: 
                sensor_id = self.unregister_sensor(message)
            else: 
                sensor_id = self.register_sensor(message)


