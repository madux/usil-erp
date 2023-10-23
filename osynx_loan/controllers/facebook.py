from odoo import http
import logging
from odoo.http import request

_logger = logging.getLogger(__name__)

# This is page access token that you get from facebook developer console.
PAGE_ACCESS_TOKEN = 'EAAaScZAEBtGkBAEJ7MOr66bxddl9S4U698KxZBFGjWniRpQ9v31RBw4wdVnWZBJgvbNvGqIjGjTBDafHLBKh07OZAUN3JP8luTjQLkd0Jor6AXPLsaTabhXLx7dgGMGEpbZCZBTLk5j3qGxfitP1msaTPpVwZC8amh2ZC5Wxkr524xilK65Q7GZBv'
# This is API key for facebook messenger.
API = "https://graph.facebook.com/v13.0/me/messages?access_token=" + PAGE_ACCESS_TOKEN


class FacebookChat(http.Controller):
    @http.route('/', auth='public', methods=["GET"])
    def fbverify(self, **rec):
        _logger.info("Receiving Messages...")
        _logger.info(rec)
        if rec.get("hub.mode") == "subscribe" and rec.get("hub.challenge"):
            if not rec.get("hub.verify_token") == "osynx_chatbot":
                return "Verification token missmatch"
            return rec['hub.challenge']

    @http.route('/', auth='public', methods=["POST"])
    def fbwebhook(self, **rec):
        _logger.info(">>>>>>>>>>>>>>>>>>>>")
        _logger.info(rec)

        if request.jsonrequest:
            _logger.info("Getting Bot updates...")
            data = request.jsonrequest
            _logger.info(data)
        try:
            # Read messages from facebook messanger.
            message = data['entry'][0]['messaging'][0]['message']
            sender_id = data['entry'][0]['messaging'][0]['sender']['id']
            if message['text'] == "hi":
                request_body = {
                    "recipient": {
                        "id": sender_id
                    },
                    "message": {
                        "text": "hello, world!"
                    }
                }
                response = request.post(API, json=request_body).json()

                return response
        except Exception as e:
            _logger.info(Warning(e))



# from odoo import http
# import logging
# from odoo.http import request
# import random
# from pymessenger.bot import Bot
#
# ACCESS_TOKEN = 'EAAaScZAEBtGkBAEJ7MOr66bxddl9S4U698KxZBFGjWniRpQ9v31RBw4wdVnWZBJgvbNvGqIjGjTBDafHLBKh07OZAUN3JP8luTjQLkd0Jor6AXPLsaTabhXLx7dgGMGEpbZCZBTLk5j3qGxfitP1msaTPpVwZC8amh2ZC5Wxkr524xilK65Q7GZBv'
# VERIFY_TOKEN = 'osynx_chatbot'
# bot = Bot(ACCESS_TOKEN)
#
# class FacebookChat(http.Controller):
#     #We will receive messages that Facebook sends our bot at this endpoint
#     @http.route("/", methods=['GET', 'POST'])
#     def receive_message(self, **rec):
#         if request.method == 'GET':
#             """Before allowing people to message your bot, Facebook has implemented a verify token
#             that confirms all requests that your bot receives came from Facebook."""
#             token_sent = request.args.get("hub.verify_token")
#             return self.verify_fb_token(token_sent)
#         #if the request was not get, it must be POST and we can just proceed with sending a message back to user
#         else:
#             # get whatever message a user sent the bot
#            output = request.get_json()
#            for event in output['entry']:
#               messaging = event['messaging']
#               for message in messaging:
#                 if message.get('message'):
#                     #Facebook Messenger ID for user so we know where to send response back to
#                     recipient_id = message['sender']['id']
#                     if message['message'].get('text'):
#                         response_sent_text = self.get_message()
#                         self.send_message(recipient_id, response_sent_text)
#                     #if user sends us a GIF, photo,video, or any other non-text item
#                     if message['message'].get('attachments'):
#                         response_sent_nontext = self.get_message()
#                         self.send_message(recipient_id, response_sent_nontext)
#         return "Message Processed"
#
#
#     def verify_fb_token(token_sent):
#         #take token sent by facebook and verify it matches the verify token you sent
#         #if they match, allow the request, else return an error
#         if token_sent == VERIFY_TOKEN:
#             return request.args.get("hub.challenge")
#         return 'Invalid verification token'
#
#
#     #chooses a random message to send to the user
#     def get_message(self):
#         sample_responses = ["You are stunning!", "We're proud of you.", "Keep on being you!", "We're greatful to know you :)"]
#         # return selected item to the user
#         return random.choice(sample_responses)
#
#     #uses PyMessenger to send response to user
#     def send_message(self, recipient_id, response):
#         #sends user the text message provided via input response parameter
#         bot.send_text_message(recipient_id, response)
#         return "success"

