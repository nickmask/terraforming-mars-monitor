import requests
import time
from datetime import datetime
import os
import logging
import sys
import json
from flask import Flask, request

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class TerraformingMarsMonitor:
    def __init__(self):
        self.base_url = "https://terraforming-mars.herokuapp.com"
        self.game_id = os.environ.get('GAME_ID', 'gca44cdf55303')
        self.current_state = None
        
        # WhatsApp credentials and verification
        self.whatsapp_token = os.environ.get('WHATSAPP_TOKEN')
        self.whatsapp_phone_id = os.environ.get('WHATSAPP_PHONE_ID')
        self.webhook_verify_token = os.environ.get('WEBHOOK_VERIFY_TOKEN', 'your_verification_token')
        
        # Player phone number mapping from environment variables
        self.player_phones = {
            "Katrin": os.environ.get('KATRIN_PHONE'),
            "Joe": os.environ.get('JOE_PHONE'),
            "Nick": os.environ.get('NICK_PHONE'),
            "Tess": os.environ.get('TESS_PHONE')
        }
        
        # Create reverse lookup for phone numbers to player names
        self.phone_to_player = {phone: name for name, phone in self.player_phones.items() if phone}
        
        # Verify configuration
        if not all([self.whatsapp_token, self.whatsapp_phone_id]):
            logging.error("Missing required WhatsApp environment variables!")
            raise ValueError("Missing required WhatsApp environment variables!")

    def setup_webhook_server(self):
        """Setup Flask server for webhook with verification"""
        app = Flask(__name__)

        @app.route('/webhook', methods=['GET'])
        def verify_webhook():
            """Handle webhook verification from WhatsApp"""
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')

            logging.info(f"Received verification request - Mode: {mode}, Token: {token}")

            if mode and token:
                if mode == 'subscribe' and token == self.webhook_verify_token:
                    logging.info("Webhook verified successfully!")
                    return challenge, 200
                else:
                    logging.warning("Webhook verification failed")
                    return 'Verification failed', 403
            return 'Invalid verification request', 400

        @app.route('/webhook', methods=['POST'])
        def webhook():
            """Handle incoming webhook messages"""
            try:
                if request.is_json:
                    data = request.get_json()
                    logging.info(f"Received webhook data: {json.dumps(data, indent=2)}")
                    
                    if 'entry' in data and data['entry']:
                        entry = data['entry'][0]
                        if 'changes' in entry and entry['changes']:
                            change = entry['changes'][0]
                            if 'value' in change and 'messages' in change['value']:
                                message = change['value']['messages'][0]
                                from_number = message['from']
                                message_text = message['text']['body']
                                logging.info(f"Processing message: {message_text} from {from_number}")
                                self.handle_incoming_message(message_text, from_number)
                    return 'OK', 200
                else:
                    logging.warning("Received non-JSON webhook data")
                    return 'Invalid format', 400
            except Exception as e:
                logging.error(f"Error processing webhook: {e}")
                return 'Error processing webhook', 500

        # Start the Flask app
        port = int(os.environ.get('WEBHOOK_PORT', '3000'))
        logging.info(f"Starting webhook server on port {port}")
        app.run(host='0.0.0.0', port=port)

    def handle_incoming_message(self, message_text, from_number):
        """Handle incoming WhatsApp messages"""
        # Check if the number belongs to one of our players
        if from_number not in self.phone_to_player:
            logging.warning(f"Received message from unknown number: {from_number}")
            return
            
        player_name = self.phone_to_player[from_number]
        logging.info(f"Processing command from {player_name}: {message_text}")
        
        if message_text.lower().startswith('!gameid '):
            new_game_id = message_text.split(' ')[1].strip()
            if self.validate_game_id(new_game_id):
                old_game_id = self.game_id
                self.game_id = new_game_id
                
                # Notify all players of the change
                update_message = (
                    f"🎲 Game ID updated by {player_name}\n"
                    f"Old game: {old_game_id}\n"
                    f"New game: {new_game_id}"
                )
                
                for phone in self.player_phones.values():
                    if phone:
                        self.send_whatsapp_message(phone, update_message)
                
                # Reset current state
                self.current_state = None
                logging.info(f"Game ID updated to {new_game_id} by {player_name}")
            else:
                self.send_whatsapp_message(
                    from_number,
                    f"❌ Invalid game ID: {new_game_id}\n"
                    "Make sure the game exists and the ID is correct"

    def run(self):
        """Main monitoring loop"""
        logging.info("Starting Terraforming Mars game monitor...")
        logging.info(f"Monitoring game ID: {self.game_id}")
        
        # Start webhook server in a separate thread
        import threading
        webhook_thread = threading.Thread(target=self.setup_webhook_server)
        webhook_thread.daemon = True
        webhook_thread.start()
        
        # Send startup message with instructions
        startup_message = (
            "🎮 Terraforming Mars monitor is now active!\n"
            f"Current game ID: {self.game_id}\n"
            "Send '!gameid <new-id>' to update the game"
        )
        for phone in self.player_phones.values():
            if phone:
                self.send_whatsapp_message(phone, startup_message)
        
        while True:
            try:
                game_state = self.get_game_state()
                self.notify_players(game_state)
                time.sleep(5)
                
            except Exception as e:
                logging.error(f"Error in monitor loop: {e}")
                time.sleep(5)

if __name__ == "__main__":
    monitor = TerraformingMarsMonitor()
    monitor.run()