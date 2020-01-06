### Send a notification through Telegram
## HOW IT WORKS: 
## DEPENDENCIES:
# OS:
# Python: python-telegram-bot
## CONFIGURATION:
# required: bot_token, chat_id
# optional: 
## COMMUNICATION:
# INBOUND: 
# - NOTIFY: receive a notification request
# OUTBOUND: 

import telegram.ext

from sdk.python.module.notification import Notification

import sdk.python.utils.exceptions as exception

class Telegram_messenger(Notification):
    # What to do when initializing
    def on_init(self):
        # request required configuration files
        self.config_schema = 1
        self.add_configuration_listener(self.fullname, "+", True)

    # What to do when running
    def on_start(self):
        pass
        
    # What to do when shutting down
    def on_stop(self):
        pass
        
   # What to do when ask to notify
    def on_notify(self, severity, text):
        self.log_debug("saying: "+text)
        bot = telegram.Bot(self.config["bot_token"])
        bot.send_message(chat_id=self.config["chat_id"], text=text)

     # What to do when receiving a new/updated configuration for this module    
    def on_configuration(self, message):
        # module's configuration
        if message.args == self.fullname and not message.is_null:
            if message.config_schema != self.config_schema: 
                return False
            if not self.is_valid_configuration(["bot_token", "chat_id"], message.get_data()): return False
            self.config = message.get_data()
