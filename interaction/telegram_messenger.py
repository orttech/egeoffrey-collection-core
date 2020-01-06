### Connect to a Telegram group hannel as a bot and interact with the user
## HOW IT WORKS: ask the bot anything by using the command handler defined in the configuration file (e.g. /housebot hello!)
## DEPENDENCIES:
# OS:
# Python: python-telegram-bot
## CONFIGURATION:
# required: bot_token, bot_name, channel
# optional: 
## COMMUNICATION:
# INBOUND: 
# OUTBOUND: 
# - controller/chatbot ASK: ask the chatbot how to respond to the request

import json
import time
import base64
import logging
from telegram.ext import Updater, CommandHandler

from sdk.python.module.interaction import Interaction
from sdk.python.module.helpers.message import Message

import sdk.python.utils.exceptions as exception

# interact through telegram
class Telegram_messenger(Interaction):
    # What to do when initializing
    def on_init(self):
        # variables
        self.updater = None
        # constants
        self.tmp_file = "/tmp/eGeoffrey_telegram_image.jpg"
        # request required configuration files
        self.config_schema = 1
        self.add_configuration_listener(self.fullname, "+", True)

    def process_message(self, update, context):
        # clean up request
        request = update.message.text.replace("/"+self.config["command_handler"]+" ", "").lower()
        # ask our chatbot what to respond
        message = Message(self)
        message.recipient = "controller/chatbot"
        message.command = "ASK"
        message.set("request", request)
        message.set("accept", ["text", "image"])
        self.sessions.register(message, {
            "update": update
        })
        self.send(message)
    
    # What to do when running
    def on_start(self):
        # configure logging
        #logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.DEBUG)
        # connect the bot
        self.updater = Updater(self.config["bot_token"], use_context=True)
        # register the handler
        self.updater.dispatcher.add_handler(CommandHandler(self.config["command_handler"], self.process_message))
        # start polling for new messages
        self.updater.start_polling()
        
    # What to do when shutting down
    def on_stop(self):
        self.updater.stop()
        
    # What to do when receiving a request for this module    
    def on_message(self, message):
        # handle response from the chatbot
        if message.sender == "controller/chatbot" and message.command == "ASK":
            session = self.sessions.restore(message)
            if session is None: return
            update = session["update"]
            type = message.get("type")
            content = message.get("content")
            if type == "text":
                # post the text response
                update.message.reply_text(content)
            elif type == "image":
                # save the file first
                f = open(self.tmp_file, "w")
                f.write(base64.b64decode(content))
                f.close()
                # upload the file
                update.message.reply_photo(open(self.tmp_file, 'rb'), caption=message.get("description"))
        
     # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self, message):
        # module's configuration
        if message.args == self.fullname and not message.is_null:
            if message.config_schema != self.config_schema: 
                return False
            if not self.is_valid_configuration(["bot_token", "command_handler"], message.get_data()): return False
            self.config = message.get_data()