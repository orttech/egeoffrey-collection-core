### service/csv: retrieve values from a csv file
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
#   required: csv_file, value_position
#   optional: filter, filter_position, date_position, date_format, prefix
# OUTBOUND: 

import datetime
import time
import json

from sdk.python.module.service import Service
import sdk.python.utils.exceptions as exception
from sdk.python.utils.datetimeutils import DateTimeUtils

import sdk.python.utils.web

class Csv(Service):
    # What to do when initializing
    def on_init(self):
        pass
        
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
            if not self.is_valid_configuration(["csv_file", "value_position"], message.get_data()): return
            csv_file = message.get("csv_file")
            value_position = message.get("value_position")
            filter = message.get("filter") if message.has("filter") else None
            filter_position = message.get("filter_position") if message.has("filter_position") else None
            date_position = message.get("date_position") if message.has("date_position") else None
            date_format = message.get("date_format") if message.has("date_format") else None
            prefix = message.get("prefix") if message.has("filter_position") else None
            # if the raw data is cached, take it from there, otherwise request the data and cache it
            cache_key = "/".join([csv_file])
            if self.cache.find(cache_key): 
                data = self.cache.get(cache_key)
            else:
                # read and return the content of file (in json)
                if csv_file.startswith("http://") or csv_file.startswith("https://"):
                    # if the filename is a url retrieve the data
                    try:
                        data = json.dumps(sdk.python.utils.web.get(csv_file).split("\n"))
                    except Exception,e: 
                        self.log_error("unable to connect to "+csv_file+": "+exception.get(e))
                        return
                else:
                    # otherwise load the file from the filesystem
                    with open(csv_file) as file:
                        data = json.dumps(file.readlines())
                    file.close()
                self.cache.add(cache_key, data)
            message.reply()
            data = json.loads(data)
            # parse the file
            self.log_debug("file "+csv_file+" has "+str(len(data))+" lines")
            line_number = 0
            for line in data:
                line_number = line_number+1
                try: 
                    message.clear()
                    entry = line.split(',')
                    # if a filter is defined, ignore the line if the filter is not found
                    if filter is not None and entry[filter_position-1] != filter: continue
                    # if a prefix is defined, filter based on it
                    if prefix is not None and not entry[value_position-1].startswith(prefix): continue
                    # generate the timestamp
                    if "date_position" is not None:
                        date = datetime.datetime.strptime(entry[date_position-1], date_format)
                        message.set("timestamp", int(time.mktime(date.timetuple())))
                    # strip out the measure from the value
                    value = entry[value_position-1]
                    # if a measure prefix was defined, remove it
                    if prefix is not None: value.replace(prefix, "")
                    # set the value
                    message.set("value", value)
                    # send the response back
                    self.send(message)
                except Exception,e: 
                    self.log_warning("unable to parse line "+str(line_number)+", skipping: "+exception.get(e))
                    continue

    # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self,message):
        # register/unregister the sensor
        if message.args.startswith("sensors/"):
            if message.is_null: 
                sensor_id = self.unregister_sensor(message)
            else: 
                sensor_id = self.register_sensor(message)

