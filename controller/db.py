### controller/db: accept database requests and serves responses back
## HOW IT WORKS: 
## DEPENDENCIES:
# OS: python-redis
# Python: 
## CONFIGURATION:
# required: hostname, port, database
# optional: 
## COMMUNICATION:
# INBOUND: 
# - SAVE: save a new measure for a sensor
# - SAVE_ALERT: save a new alert
# - CALC_HOUR_STATS: calculate hourly aggregated stats
# - CALC_DAY_STATS: calculate daily aggregated stats
# - PURGE_SENSOR: delete old measures from db
# - PURGE_ALERT: purge old alerts from db
# - DELETE_SENSOR: delete from the db the data associated to a sensor
# - GET: return measures from the db
# - GET_ELAPSED: return the elapsed time since the measure was taken
# - GET_TIMESTAMP: return the timestamp of the measure
# - GET_DISTANCE: return the distance from the measure
# - GET_POSITION: return the name of the position
# - GET_COUNT: return the number of measures of a given timeframe
# OUTBOUND: 
# - */* SAVED: notify a new measure has been saved

import time
import redis
import re
import os
import json
import datetime
from math import radians, cos, sin, asin, sqrt

from sdk.python.module.controller import Controller
from sdk.python.module.helpers.message import Message
from sdk.python.utils.datetimeutils import DateTimeUtils
import sdk.python.utils.exceptions as exception

import sdk.python.constants
import sdk.python.utils.numbers
import sdk.python.utils.strings


class Db(Controller):
    # What to do when initializing    
    def on_init(self):
        # constants
        self.root_key = "eGeoffrey"
        self.sensors_key = self.root_key+"/sensors"
        self.alerts_key = self.root_key+"/alerts"
        self.logs_key = self.root_key+"/logs"
        self.version_key = self.root_key+"/version"
        self.query_debug = False
        # module's configuration
        self.config = {}
        # database object
        self.db = None
        self.db_connected = False
        self.db_schema_version = 1
        # date/time helper
        self.date = None
        self.house = None
        # configuration override
        self.hostname = os.getenv("EGEOFFREY_DATABASE_HOSTNAME", None)
        self.port = os.getenv("EGEOFFREY_DATABASE_PORT", None)
        self.database = os.getenv("EGEOFFREY_DATABASE_NUMBER", None)
        # request required configuration files
        self.config_schema = 1
        self.add_configuration_listener(self.fullname, "+", True)
        self.add_configuration_listener("house", 1, True)
    
    # connect to the database
    def connect(self):
        hostname = self.hostname if self.hostname is not None else self.config["hostname"]
        port = self.port if self.port is not None else self.config["port"]
        database = self.database if self.database is not None else self.config["database"]
        while not self.db_connected:
            try: 
                self.log_debug("Connecting to database "+str(database)+" at "+hostname+":"+str(port))
                self.db = redis.StrictRedis(host=hostname, port=port, db=database)
                if self.db.ping():
                    self.log_info("Connected to database #"+str(database)+" at "+hostname+":"+str(port)+", redis version "+self.db.info().get('redis_version'))
                    self.db_connected = True
            except Exception,e:
                self.log_error("Unable to connect to "+hostname+":"+str(port))
                self.sleep(5)
                if self.stopping: break
    
    # disconnect from the database
    def disconnect(self):
        if self.db_connected: self.db.connection_pool.disconnect()
    
    # normalize the output
    def normalize_dataset(self, data, withscores, milliseconds, format_date, formatter):
        output = []
        for entry in data:
            # get the timestamp 
            timestamp = int(entry[1])
            if format_date: timestamp = self.date.timestamp2date(timestamp)
            elif milliseconds: timestamp = timestamp*1000
            # normalize the value (entry is timetime:value)
            value_string = entry[0].split(":",1)[1];
            if formatter is None:
                # no formatter provided, guess the type
                value = float(value_string) if sdk.python.utils.numbers.is_number(value_string) else str(value_string)
            else:
                # formatter provided, normalize the value
                value = sdk.python.utils.numbers.normalize(value_string, formatter)
            # normalize "None" in null
            if value == "None": value = None
            # prepare the output
            if (withscores): output.append([timestamp,value])
            else: output.append(value)
        return output

    # show the available keys applying the given filter
    def keys(self, key):
        if self.query_debug: self.log_debug("keys "+key)
        return self.db.keys(key)

    # save a value to the db
    def set(self, key, value, timestamp, log=True):
        if timestamp is None: 
            if log: self.log_warning("no timestamp provided for key "+key)
            return 
        # zadd with the scorecore	
        value = str(timestamp)+":"+str(value)
        if self.query_debug and log: self.log_debug("zadd "+key+" "+str(timestamp)+" "+str(value))
        return self.db.zadd(key, timestamp, value)

    # set a single value into the db
    def set_simple(self, key,value):
        if self.query_debug: self.log_debug("set "+str(key))
        self.db.set(key, str(value))

    # get a single value from the db
    def get(self, key):
        if self.query_debug: self.log_debug("get "+key)
        return self.db.get(key)

    # get a range of values from the db based on the timestamp
    def rangebyscore(self, key, start=None, end=None, withscores=True, milliseconds=False, format_date=False, formatter=None, max_items=None):
        if start is None: start = self.date.now()-24*3600
        if end is None: end = self.date.now()
        if self.query_debug: self.log_debug("zrangebyscore "+key+" "+str(start)+" "+str(end))
        data = self.normalize_dataset(self.db.zrangebyscore(key, start, end, withscores=True), withscores, milliseconds, format_date, formatter)
        if max_items is not None and len(data) > max_items: data = data[-max_items:]
        return data
        
    # get a range of values from the db
    def range(self, key,start=-1, end=-1, withscores=True, milliseconds=False, format_date=False, formatter=None, max_items=None):
        if self.query_debug: self.log_debug("zrange "+key+" "+str(start)+" "+str(end))
        data = self.normalize_dataset(self.db.zrange(key, start, end, withscores=True), withscores, milliseconds, format_date, formatter)
        if max_items is not None and len(data) > max_items: data = data[-max_items:]
        return data

    # delete a key
    def delete(self, key):
        if self.query_debug: self.log_debug("del "+key)
        return self.db.delete(key)

    # rename a key
    def rename(self, key,new_key):
        if self.query_debug: self.log_debug("rename "+key+" "+new_key)
        return self.db.rename(key, new_key)

    # delete all elements between a given score
    def deletebyscore(self, key,start,end):
        if self.query_debug: self.log_debug("zremrangebyscore "+key+" "+str(start)+" "+str(end))
        return self.db.zremrangebyscore(key, start, end)

    # delete all elements between a given rank
    def deletebyrank(self, key,start,end):
        if self.query_debug: self.log_debug("zremrangebyrank "+key+" "+str(start)+" "+str(end))
        return self.db.zremrangebyrank(key, start, end)

    # check if a key exists
    def exists(self, key):
        if self.query_debug: self.log_debug("exists "+key)
        return self.db.exists(key)

    # empty the database
    def flushdb(self):
        if self.query_debug: self.log_debug("flushdb")
        return self.db.flushdb()

    # initialize an empty database
    def init_database(self):
        version = self.get_version()
        # no version found, assuming first installation
        if version is None:
            self.log_info("Setting database schema to v"+str(self.db_schema_version))
            self.set_version(self.db_schema_version)
        else:
            version = int(version)
            # already at the latest version
            if version == self.db_schema_version:
                pass
            # database schema needs to be upgraded
            elif version < self.db_schema_version: 
                pass
            # higher version, something strange is happening
            elif version > self.db_schema_version: 
                self.log_error("database schema v"+str(version)+" is higher than the supported schema v"+str(self.db_schema_version))


    # return eGeoffrey version or None
    def get_version(self):
        version_key = self.version_key
        if not self.exists(version_key): return None
        return self.get(version_key)

    # set eGeoffrey version to the database
    def set_version(self, version):
        version_key = self.version_key
        self.set_simple(version_key, version)

    # calculate derived aggregations such as min, max and avg value
    def calculate(self, sensor_id, calculations, group_by, start, end):
        # set the database keys to read from and write into
        key = self.sensors_key+"/"+sensor_id
        if group_by == "hour":
            # read raw measures        
            key_to_read = key 
            # write hourly summary
            key_to_write = key+"/hour" 
            # ensure time boundaries are correct
            if start == 0 or end == 0 or end-start > 60*60:
                self.log_warning("Unable to calculate "+group_by+" statistics for "+sensor_id+": invalid time boundaries ("+start+"-"+end+")")
                return
        elif group_by == "day":
            # read hourly averages
            key_to_read = key+"/hour/avg" 
            # write daily summary
            key_to_write = key+"/day" 
            # ensure time boundaries are correct
            if start == 0 or end == 0 or end-start > 24*60*60:
                self.log_warning("Unable to calculate "+group_by+" statistics for "+sensor_id+": invalid time boundaries ("+start+"-"+end+")")
                return
        # retrieve from the database the data based on the given timeframe
        data = self.rangebyscore(key_to_read, start, end, withscores=True)
        # split between values and timestamps
        values = []
        timestamps = []
        for i in range(0,len(data)):
            timestamps.append(data[i][0])
            values.append(data[i][1])
        # calculate the derived values
        timestamp = start
        min = avg = max = rate = sum = count = count_unique = "-"
        if "avg" in calculations:
            # calculate avg
            avg = sdk.python.utils.numbers.avg(values)
            self.deletebyscore(key_to_write+"/avg", start, end)
            self.set(key_to_write+"/avg", avg, timestamp)
        if "min_max" in calculations:
            # calculate min
            min = sdk.python.utils.numbers.min(values)
            self.deletebyscore(key_to_write+"/min", start, end)
            self.set(key_to_write+"/min", min, timestamp)
            # calculate max
            max = sdk.python.utils.numbers.max(values)
            self.deletebyscore(key_to_write+"/max", start, end)
            self.set(key_to_write+"/max", max, timestamp)
        if "rate" in calculations:
            # calculate the rate of change
            rate = sdk.python.utils.numbers.velocity(timestamps, values)
            self.deletebyscore(key_to_write+"/rate", start, end)
            self.set(key_to_write+"/rate", rate, timestamp)
        if "sum" in calculations:
                # calculate the sum
                sum = sdk.python.utils.numbers.sum(values)
                self.deletebyscore(key_to_write+"/sum", start, end)
                self.set(key_to_write+"/sum", sum, timestamp)
        if "count" in calculations:
                # count the values
                count = sdk.python.utils.numbers.count(values)
                self.deletebyscore(key_to_write+"/count", start, end)
                self.set(key_to_write+"/count", count, timestamp)
        if "count_unique" in calculations:
                # count the unique values
                count_unique = sdk.python.utils.numbers.count_unique(values)
                self.deletebyscore(key_to_write+"/count_unique", start, end)
                self.set(key_to_write+"/count_unique", count_unique, timestamp)
        # broadcast value updated message
        message = Message(self)
        message.recipient = "*/*"
        message.command = "SAVED"
        message.args = sensor_id
        message.set("group_by", group_by)
        message.set("timestamp", timestamp)
        message.set("value", str(min)+","+str(avg)+","+str(max)+","+str(rate)+","+str(sum)+","+str(count)+","+str(count_unique))
        self.send(message)
        self.log_debug("["+sensor_id+"] ("+self.date.timestamp2date(timestamp)+") updating summary of the "+group_by+" (min,avg,max,rate,sum,count,count_unique): ("+str(min)+","+str(avg)+","+str(max)+","+str(rate)+","+str(sum)+","+str(count)+","+str(count_unique)+")")

    # What to do when running
    def on_start(self):
        # connect to the database
        self.connect()
        # initialize the database if needed 
        self.init_database()
        
    # What to do when shutting down
    def on_stop(self):
        # disconnect from the database
        self.disconnect()

    # What to do when receiving a request for this module    
    def on_message(self, message):
        if not self.db_connected: return # ignore the request if not connected yet
        item_id = message.args # item_id contains sensor_id, rule_id, etc.
        
        # save a timestamp:value pair in the database to the given key
        if message.command == "SAVE": 
            key = self.sensors_key+"/"+item_id
            # 1) if statistics to save the value to is explicit, set it
            if message.has("statistics"): key = key+"/"+message.get("statistics")
            # 2) check if we need to apply any retention policy before saving the new value
            if message.has("retain"):
                retain = message.get("retain")
                # if we have to keep up to "count" values, delete old values from the db
                if "count" in retain:
                    self.deletebyrank(key, 0, -retain["count"])
                # if only measures with a newer timestamp than the latest can be added, apply the policy
                if "new_only" in retain and retain["new_only"]:
                    # retrieve the latest measure's timestamp
                    last = self.range(key, -1, -1)
                    if len(last) > 0:
                        last_timestamp = last[0][0]
                        # if the measure's timestamp is older or the same, skip it
                        if message.get("timestamp") <= last_timestamp:
                            self.log_debug("["+item_id+"] ("+self.date.timestamp2date(message.get("timestamp"))+") old event, ignoring "+key+": "+str(message.get("value")))
                            return
            # 3) check if there is already something stored with the same timestamp
            old = self.rangebyscore(key, message.get("timestamp"), message.get("timestamp"))
            if len(old) > 0:
                if old[0][1] == message.get("value"):
                    # if the value is also the same, skip it
                    self.log_debug("["+item_id+"] ("+self.date.timestamp2date(message.get("timestamp"))+") already in the database, ignoring "+key+": "+str(message.get("value")))
                    return
                else: 
                    # same timestamp but different value, remove the old value so to store the new one
                    self.deletebyscore(key, message.get("timestamp"), message.get("timestamp"))
            # 4) save the new value
            self.set(key, message.get("value"), message.get("timestamp"))
            # 5) broadcast acknowledge value updated
            ack_message = Message(self)
            ack_message.recipient = "*/*"
            ack_message.command = "SAVED"
            ack_message.args = item_id
            ack_message.set("from_save", True)
            ack_message.set("timestamp", message.get("timestamp"))
            ack_message.set("value", sdk.python.utils.strings.truncate(message.get("value"), 50))
            if message.has("statistics"):
                ack_message.set("group_by", message.get("statistics").split("/")[0])
                ack_message.set("statistics", message.get("statistics"))
            self.send(ack_message)
            # 6) re-calculate the derived statistics for the hour/day
            if message.has("calculate"):
                self.calculate(item_id, message.get("calculate"), "hour", self.date.hour_start(message.get("timestamp")), self.date.hour_end(message.get("timestamp")))
                self.calculate(item_id, message.get("calculate"), "day", self.date.day_start(message.get("timestamp")), self.date.day_end(message.get("timestamp")))
        
        # save alert
        elif message.command == "SAVE_ALERT":
            key = self.alerts_key+"/"+item_id
            self.set(key, message.get_data(), self.date.now())
            self.log_debug("["+item_id+"] saving alert '"+message.get_data()+"'")
            
        # save log
        elif message.command == "SAVE_LOG":
            key = self.logs_key+"/"+item_id
            self.set(key, message.get_data(), self.date.now(), False)
        
        # calculate hourly statistics for the requested sensor
        elif message.command == "CALC_HOUR_STATS":
            self.calculate(item_id, message.get_data(), "hour", self.date.hour_start(self.date.last_hour()), self.date.hour_end(self.date.last_hour()))
        # calculate daily statistics for the requested sensor
        elif message.command == "CALC_DAY_STATS":
            self.calculate(item_id, message.get_data(), "day", self.date.day_start(self.date.yesterday()), self.date.day_end(self.date.yesterday()))
        
        # apply sensors retention policies
        elif message.command == "PURGE_SENSOR":
            sensor_id = item_id
            policies = message.get_data()
            total = 0
            # set the base database key for the sensor
            key = self.sensors_key+"/"+sensor_id
            # define which stat to purge for each dataset
            targets = {
                "raw": [""],
                "hourly": ["/hour/min","/hour/avg","/hour/max","/hour/rate"],
                "daily": ["/day/min","/day/avg","/day/max","/day/rate"],
            }
            # for each dataset, purge the associated subkeys
            for dataset, subkeys in targets.iteritems():
                if dataset not in policies: continue
                retention = policies[dataset]
                if retention == 0: continue # keep data forever
                # for each stat to purge
                for subkey in subkeys:
                    key = key+subkey
                    if self.exists(key):
                        # if the key exists, delete old data
                        deleted = self.deletebyscore(key, "-inf", self.date.now() - retention*86400)
                        self.log_debug("["+sensor_id+"] deleting from "+key+" "+str(deleted)+" old items")
                        total = total + deleted
            if total > 0: self.log_info("["+sensor_id+"] deleted "+str(total)+" old values")
            
        # apply alerts retention policies
        elif message.command == "PURGE_ALERTS":
            days = message.get_data()
            total = 0
            for severity in ["info", "warning", "alert"]:
                key = self.alerts_key+"/"+severity
                if self.exists(key):
                    deleted = self.deletebyscore(key,"-inf",self.date.now()-days*86400)
                    self.log_debug("deleting from "+severity+" "+str(deleted)+" items")
                    total = total + deleted
            if total > 0: self.log_info("deleted "+str(total)+" old alerts")

        # apply log retention policies
        elif message.command == "PURGE_LOGS":
            days = message.get_data()
            total = 0
            for severity in ["debug", "info", "warning", "error"]:
                key = self.logs_key+"/"+severity
                if self.exists(key):
                    deleted = self.deletebyscore(key,"-inf",self.date.now()-days*86400)
                    self.log_debug("deleting from "+severity+" "+str(deleted)+" items")
                    total = total + deleted
            if total > 0: self.log_info("deleted "+str(total)+" old logs")
        
        # delete a sensor from the database
        elif message.command == "DELETE_SENSOR":
            key = self.sensors_key+"/"+item_id
            self.log_info("deleting from the database sensor "+item_id)
            self.delete(key)
            self.log_debug("deleting key "+key)
            for timeframe in ["hour", "day"]:
                for stat in ["min", "avg", "max", "rate", "sum", "count", "count_unique"]:
                    self.delete(key+"/"+timeframe+"/"+stat)
                    self.log_debug("deleting key "+key+"/"+timeframe+"/"+stat)
            
        # database statistics
        elif message.command == "STATS":
            output = []
            keys = self.keys("*")
            for key in sorted(keys):
                if self.db.type(key) != "zset": continue
                data = self.range(key, 1, 1)
                start = data[0][0] if len(data) > 0 else ""
                data = self.range(key, -1, -1)
                end = data[0][0] if len(data) > 0 else ""
                value = data[0][1] if len(data) > 0 else ""
                output.append([key, self.db.zcard(key), start, end, sdk.python.utils.strings.truncate(value, 300)])
            message.reply()
            message.set_data(output)
            self.send(message)
        
        # query the database
        elif message.command.startswith("GET"):
            # 1) initialize query objecy. payload will be passed to the range* function, adding missing parameter key
            query = message.get_data().copy() if isinstance(message.get_data(), dict) else {}
            # select which area of the database to query (default to sensors)
            scope = self.sensors_key
            if "scope" in query:
                if query["scope"] == "logs": scope = self.logs_key
                if query["scope"] == "alerts": scope = self.alerts_key
                del query["scope"]
            key = scope+"/"+item_id
            query["key"] = key
            # 2) handle timeframe requests, calculate start and end
            if "timeframe" in query:
                if query["timeframe"] == "today":
                    query["start"] = self.date.day_start(self.date.now())
                    query["end"] = self.date.day_end(self.date.now())
                    query["withscores"] = False
                elif query["timeframe"] == "yesterday":
                    query["start"] = self.date.day_start(self.date.yesterday())
                    query["end"] = self.date.day_end(self.date.yesterday())
                    query["withscores"] = False
                elif query["timeframe"].startswith("last_") or query["timeframe"].startswith("next_"):
                    # expect <last|next>_xx_<hours|days>
                    action, value, unit = query["timeframe"].split("_")
                    # convert the provided value in seconds
                    value = int(value)*3600 if unit == "hours" else int(value)*86400
                    # set start/end based on the requested action
                    query["start"] = self.date.now() - int(value) if action == "last" else self.date.now()
                    query["end"] = self.date.now() if action == "last" else self.date.now() + int(value)
                    query["withscores"] = True
                    query["milliseconds"] = True
                del query["timeframe"]
            # 3) if start and/or end are timestamps, use rangebyscore, otherwise use range
            if "start" in query and query["start"] > 1000:
                function = self.rangebyscore
            elif "end" in query and query["end"] > 1000:
                function = self.rangebyscore
            else: 
                function = self.range
            # reply to the requesting module
            message.reply()
            # 4) set if we need timestamps together with the values
            if message.command == "GET_ELAPSED" or message.command == "GET_TIMESTAMP": 
                query["withscores"] = True
            if "withscores" not in query: query["withscores"] = False
            # 5) if range is requested, start asking for min first
            is_range = False
            if query["key"].endswith("/range"):
                is_range = True
                query["key"] = re.sub("/range$", "/min", query["key"])
            # 6) call the function mapping parameters with message payload input
            data = function(**query)
            # 7) postprocess if needed
            if is_range and len(data) > 0:
                # if a range is requested, ask for the max and combine the results
                query["key"] = re.sub("/min$", "/max", query["key"])
                query["withscores"] = False
                data_max = function(**query)
                for i, item in enumerate(data):
                    # ensure data_max has a correspondent value
                    if i < len(data_max):
                        if (isinstance(item,list)): data[i].append(data_max[i])
                        else: data.append(data_max[i])
            # elapsed since the measure was taken is requested, calculate the time difference in seconds
            if message.command == "GET_ELAPSED":
                if len(data) == 0: 
                    data = []
                else: 
                    time_diff = (self.date.now() - data[0][0])/60
                    data = [time_diff]
            # the timestamp of the measure is requested, return it
            elif message.command == "GET_TIMESTAMP":
                if len(data) == 0: data = []
                else: data = [data[0][0]]
            # the distance of the measure from this house is requested
            elif message.command == "GET_DISTANCE":
                if len(data) == 0: return []
                # get position (only the first one if multiple are provided)
                try:
                    position = json.loads(data[0])
                except Exception,e: 
                    self.log_warning("unable to get the distance from an invalid position: "+str(data)+" - "+exception.get(e))
                    return
                if "longitude" not in position or "latitude" not in position: 
                    self.log_warning("invalid position provided: "+str(position))
                    return
                # convert decimal degrees to radians 
                lon1, lat1, lon2, lat2 = map(radians, [position["longitude"], position["latitude"], self.house["longitude"], self.house["latitude"]])
                # haversine formula 
                dlon = lon2 - lon1 
                dlat = lat2 - lat1 
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a)) 
                distance = 6367 * c
                if self.house["units"] == "imperial": distance = distance/1.609
                data = [int(distance)]
            # the text associated to the position is requested
            elif message.command == "GET_POSITION_TEXT":
                if len(data) == 0: return []
                try:
                    position = json.loads(data[0])
                except Exception,e: 
                    self.log_warning("unable to get the text from an invalid position: "+str(data)+" - "+exception.get(e))
                    return
                if "text" not in position: 
                    self.log_warning("text missing: "+str(position))
                    return
                data = [position["text"]]
            # the label associated to the position is requested
            elif message.command == "GET_POSITION_LABEL":
                if len(data) == 0: return []
                try:
                    position = json.loads(data[0])
                except Exception,e: 
                    self.log_warning("unable to get the label from an invalid position: "+str(data)+" - "+exception.get(e))
                    return
                if "label" not in position: 
                    self.log_warning("label missing: "+str(position))
                    return
                data = [position["label"]]
            # the timestamp of the measure is requested, return it
            elif message.command == "GET_SCHEDULE":
                if len(data) != 1: return []
                # the calendar string is at position 0
                try:
                    calendar = json.loads(data[0])
                except Exception,e: 
                    self.log_warning("unable to parse calendar's data: "+str(data)+" - "+exception.get(e))
                    return []
                # the list of events is at position 1
                if len(calendar) != 2: return []
                events = json.loads(calendar[1])
                found = False
                for event in events:
                    # generate the timestamp of start and end date
                    start_date = datetime.datetime.strptime(event["start_date"],"%Y-%m-%dT%H:%M:%S.000Z")
                    start_timestamp = self.date.timezone(self.date.timezone(int(time.mktime(start_date.timetuple()))))
                    end_date = datetime.datetime.strptime(event["end_date"],"%Y-%m-%dT%H:%M:%S.000Z")
                    end_timestamp = self.date.timezone(self.date.timezone(int(time.mktime(end_date.timetuple()))))
                    now_ts = self.date.now()
                    # check if we are within an event
                    if now_ts > start_timestamp and now_ts < end_timestamp: 
                        found = True
                        data = [event["text"]]
                if not found: data = [""]
            # a count of the measures taken during the timeframe is requested,  count the values
            elif message.command == "GET_COUNT":
                data = [len(data)]
            # 8) attach the result to the message payload
            message.set("data", data)
            # 10) send the response back
            self.log_debug(message.command+" from "+message.sender+" for "+str(query)+" returning "+str(message.get_data()))
            self.send(message)
            
     # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self, message):
        # ignore deleted configuration files while service is restarting
        if message.is_null: return
        # we need house timezone for querying the database
        if message.args == "house" and not message.is_null:
            if not self.is_valid_configuration(["timezone"], message.get_data()): return False
            self.date = DateTimeUtils(message.get("timezone"))
            self.house = message.get_data()
        # module's configuration
        elif message.args == self.fullname:     
            if message.config_schema != self.config_schema: 
                return False
            # ensure the configuration file contains all required settings
            if not self.is_valid_configuration(["hostname", "port", "database"], message.get_data()): return False
            # if this is an updated configuration file, disconnect and reconnect
            if self.config: 
                self.disconnect()
                self.config = message.get_data()
                self.connect()
            else: self.config = message.get_data()
                