### service/mqtt: interact with sensors through a mqtt broker
## HOW IT WORKS: 
## DEPENDENCIES:
# OS: 
# Python: paho-mqtt
## CONFIGURATION:
# required: hostname, port
# optional: username, password
## COMMUNICATION:
# INBOUND: 
# - OUT: 
#   required: topic, value
#   optional: 
# OUTBOUND:
# - controller/hub IN: 
#   required: topic
#   optional: 

import paho.mqtt.client as mqtt

from sdk.python.module.service import Service
from sdk.python.module.helpers.message import Message

import sdk.python.utils.exceptions as exception

class Mqtt(Service):
    # What to do when initializing
    def on_init(self):
        # TODO: reusing sdk mqtt class?
        # configuration
        self.config = {}
        # track the topics subscribed
        self.topics_to_subscribe = []
        self.topics_subscribed = []
        # mqtt object
        self.client = mqtt.Client()
        self.mqtt_connected = False
        # require configuration before starting up
        self.config_schema = 1
        self.add_configuration_listener(self.fullname, "+", True)
        
    # What to do when running
    def on_start(self):
        # receive callback when conneting
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.log_debug("Connected to the MQTT gateway ("+str(rc)+")")
                # subscribe to previously queued topics
                for topic in self.topics_to_subscribe:
                    self.subscribe_topic(topic)
                self.topics_to_subscribe = []
                self.mqtt_connected = True
            
        # receive a callback when receiving a message
        def on_message(client, userdata, msg):
            # find the sensor matching the topic
            for sensor_id in self.sensors:
                sensor = self.sensors[sensor_id]
                if mqtt.topic_matches_sub(sensor["topic"], msg.topic):
                    self.log_debug("received "+str(msg.payload)+" for "+sensor_id+" on topic "+str(msg.topic))
                    # prepare the message
                    message = Message(self)
                    message.recipient = "controller/hub"
                    message.command = "IN"
                    message.args = sensor_id
                    message.set("value", msg.payload)
                    # send the measure to the controller
                    self.send(message)
            
        # connect to the gateway
        try: 
            self.log_info("Connecting to MQTT gateway on "+self.config["hostname"]+":"+str(self.config["port"]))
            password = self.config["password"] if "password" in self.config else ""
            if "username" in self.config: self.client.username_pw_set(self.config["username"], password=password)
            self.client.connect(self.config["hostname"], self.config["port"], 60)
        except Exception,e:
            self.log_warning("Unable to connect to the MQTT gateway "+self.config["hostname"]+":"+str(self.config["port"])+": "+exception.get(e))
            return
        # set callbacks
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        # start loop (in the background)
        # TODO: reconnect
        try: 
            self.client.loop_start()
        except Exception,e: 
            self.log_error("Unexpected runtime error: "+exception.get(e))
    
    # What to do when shutting down
    def on_stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        
    # What to do when receiving a request for this module
    def on_message(self, message):
        sensor_id = message.args
        if message.command == "OUT":
            if not self.mqtt_connected: return
            if not self.is_valid_configuration(["topic", "value"], message.get_data()): return
            topic = message.get("topic")
            data = message.get("value")
            # send the message
            self.log_info("sending message "+str(data)+" to "+topic)
            self.client.publish(topic, str(data))

    # subscribe to a mqtt topic
    def subscribe_topic(self, topic):
        self.log_debug("Subscribing to the MQTT topic "+topic)
        self.topics_subscribed.append(topic)
        self.client.subscribe(topic)        

    # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self,message):
        # module's configuration
        if message.args == self.fullname and not message.is_null:
            if message.config_schema != self.config_schema: 
                return False
            if not self.is_valid_configuration(["hostname", "port"], message.get_data()): return False
            self.config = message.get_data()
        # register/unregister the sensor
        if message.args.startswith("sensors/"):
            if message.is_null: 
                sensor_id = message.args.replace("sensors/","")
                # unsubscribe from the topic
                if sensor_id in self.sensors:
                    configuration = self.sensors[sensor_id]
                    self.client.unsubscribe(configuration["topic"])
                self.unregister_sensor(message)
            else: 
                # TODO: certificate, client_id, ssl
                sensor_id = self.register_sensor(message, ["topic"])
                if sensor_id is not None:
                    # subscribe to the topic if connected, otherwise queue the request
                    configuration = self.sensors[sensor_id]
                    if self.mqtt_connected: 
                        self.subscribe_topic(configuration["topic"])
                    else: 
                        self.topics_to_subscribe.append(configuration["topic"])
