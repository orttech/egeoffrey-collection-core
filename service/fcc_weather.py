### service/fcc_weather: retrieve weather information from https://fcc-weather-api.glitch.me/
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
#   required: request (temperature|pressure|humidity|wind|wind_dir|condition|description|visibility|clouds), latitude, longitude
#   optional: 
# OUTBOUND: 

import json
import datetime
import time
 
from sdk.python.module.service import Service
from sdk.python.utils.datetimeutils import DateTimeUtils

import sdk.python.utils.web
import sdk.python.utils.numbers
import sdk.python.utils.exceptions as exception

class Fcc_weather(Service):
   # What to do when initializing
    def on_init(self):
        # constants
        self.url = 'https://fcc-weather-api.glitch.me/api/current'

    # set the value and timestamp to the message
    def set_measure(self, message, value, timestamp):
        message.set("value", value)
        message.set("timestamp", int(timestamp))
    
    # What to do when running    
    def on_start(self):
        pass
    
    # What to do when shutting down
    def on_stop(self):
        pass

    # What to do when receiving a request for this module
    def on_message(self, message):
        if message.command == "IN":
            if not self.is_valid_configuration(["request", "latitude", "longitude"], message.get_data()): return
            sensor_id = message.args
            request = message.get("request")
            location = "lat="+str(message.get("latitude"))+"&lon="+str(message.get("longitude"))
            # if the raw data is cached, take it from there, otherwise request the data and cache it
            cache_key = location
            if self.cache.find(cache_key): 
                data = self.cache.get(cache_key)
            else:
                url = self.url+"?"+location
                try:
                    data = sdk.python.utils.web.get(url)
                except Exception,e: 
                    self.log_error("unable to connect to "+url+": "+exception.get(e))
                    return
                self.cache.add(cache_key,data)
            # parse the raw data
            try: 
                parsed_json = json.loads(data)
            except Exception,e: 
                self.log_error("invalid JSON returned")
                return
            if not "cod" in parsed_json:
                self.log_error("JSON missing 'cod': "+str(parsed_json))
                return
            if int(parsed_json["cod"]) != 200:
                self.log_error("Invalid response: "+str(parsed_json["message"]))
                return
            # reply to the requesting module 
            message.reply()
            entry = parsed_json
            if request == "temperature":
                self.set_measure(message, entry["main"]["temp"], entry["dt"])
            elif request == "humidity":
                self.set_measure(message, entry["main"]["humidity"], entry["dt"])
            elif request == "wind":
                self.set_measure(message, entry["wind"]["speed"], entry["dt"])
            elif request == "wind_dir":
                degrees = entry["wind"]["deg"]
                direction = "question"
                if direction >= 315 or direction <= 45: direction = "arrow-down"
                elif direction > 45 and direction <= 135: direction = "arrow-left"
                elif direction > 135 and direction <= 225: direction = "arrow-up"
                elif direction > 225 and direction <= 315: direction = "arrow-right"
                self.set_measure(message, direction, entry["dt"])
            elif request == "pressure":
                self.set_measure(message, entry["main"]["pressure"], entry["dt"])
            elif request == "visibility":
                self.set_measure(message, entry["visibility"], entry["dt"])
            elif request == "clouds":
                self.set_measure(message, entry["clouds"]["all"], entry["dt"])
            elif request == "condition":
                code = entry["weather"][0]["main"]
                value = "question"
                if code in ["Thunderstorm"]: value = "cloud-showers-heavy"
                elif code in ["Drizzle", "Mist", "Smoke", "Haze", "Dust", "Fog", "Sand", "Ash", "Squall", "Tornado"]: value = "smog"
                elif code in ["Rain"]: value = "cloud-rain"
                elif code in ["Snow"]: value = "snowflake"
                elif code in ["Clear"]: value = "sun"
                elif code in ["Clouds"]: value = "cloud"
                self.set_measure(message, value, entry["dt"])
            elif request == "description":
                self.set_measure(message,  entry["weather"][0]["description"], entry["dt"])
                message.set("value", entry["weather"][0]["description"])
            else: 
                self.log_error("invalid request for "+sensor_id+": "+str(message.get("request")))
                return
            # send the response back
            self.send(message)

    # What to do when receiving a new/updated configuration for this module
    def on_configuration(self,message):
        # register/unregister the sensor
        if message.args.startswith("sensors/"):
            if message.is_null: 
                sensor_id = self.unregister_sensor(message)
            else: 
                sensor_id = self.register_sensor(message)

