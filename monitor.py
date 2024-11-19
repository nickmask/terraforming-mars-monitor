import requests
import time
from datetime import datetime
import os
import logging
import sys
import json

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
        
        # WhatsApp credentials
        self.whatsapp_token = os.environ.get('WHATSAPP_TOKEN')
        self.whatsapp_phone_id = os.environ.get('WHATSAPP_PHONE_ID')
        
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

    def handle_incoming_message(self, message_text, from_number):
        """Handle incoming WhatsApp messages"""
        # Check if the number belongs to one of our players
        if from_number not in self.phone_to_player:
            logging.warning(f"Received message from unknown number: {from_number}")
            return
            
        player_name = self.phone_to_player[from_number]
        
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
                )
                
    def validate_game_id(self, game_id):
        """Validate that a game ID exists"""
        url = f"{self.base_url}/api/game"
        params = {"id": game_id}
        
        try:
            response = requests.get(url, params=params)
            return response.status_code == 200
        except:
            return False

    def send_whatsapp_message(self, phone_number, message):
        """Send a WhatsApp message to a specific number"""
        if not phone_number:
            logging.warning(f"No phone number provided for message: {message}")
            return
            
        url = f"https://graph.facebook.com/v21.0/{self.whatsapp_phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        try:
            logging.info(f"Sending WhatsApp message to: {phone_number}")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                logging.info(f"Message sent successfully to {phone_number}: {message}")
            else:
                logging.error(f"Failed to send to {phone_number}: {response.status_code}")
                logging.error(f"Error: {response.text}")
        except Exception as e:
            logging.error(f"Error sending to {phone_number}: {e}")

    def get_game_state(self):
        """Fetch the current game state"""
        url = f"{self.base_url}/api/game"
        params = {"id": self.game_id}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error fetching game state: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error checking game state: {e}")
            return None

    def get_player_name_by_color(self, color, players):
        """Get player name from their color"""
        for player in players:
            if player['color'] == color:
                return player['name']
        return None

    def notify_players(self, game_state):
        """Send notifications based on game state changes"""
        if not game_state:
            return

        # Check for research phase
        if game_state.get('phase') == 'research':
            if self.current_state is None or self.current_state.get('phase') != 'research':
                # Send research notification to all players
                message = "🔬 It's research time!"
                for phone in self.player_phones.values():
                    if phone:  # Only send if phone number is configured
                        self.send_whatsapp_message(phone, message)
        else:
            # Check for player turn changes
            active_color = game_state.get('activePlayer')
            if active_color:
                active_player_name = self.get_player_name_by_color(active_color, game_state.get('players', []))
                
                if active_player_name:
                    # Only send message if it's a new turn
                    if (self.current_state is None or 
                        self.current_state.get('activePlayer') != active_color):
                        
                        # Get phone number for active player
                        phone = self.player_phones.get(active_player_name)
                        if phone:
                            message = f"🎮 It's your turn!"
                            self.send_whatsapp_message(phone, message)
                        else:
                            logging.warning(f"No phone number configured for {active_player_name}")
        
        # Update current state
        self.current_state = game_state

    def setup_webhook_server(self):
        """Setup Flask server for webhook"""
        from flask import Flask, request

        app = Flask(__name__)

        @app.route('/webhook', methods=['POST'])
        def webhook():
            if request.is_json:
                data = request.get_json()
                try:
                    message = data['entry'][0]['changes'][0]['value']['messages'][0]
                    from_number = message['from']
                    message_text = message['text']['body']
                    self.handle_incoming_message(message_text, from_number)
                except Exception as e:
                    logging.error(f"Error processing webhook: {e}")
            return 'OK', 200

        app.run(host='0.0.0.0', port=int(os.environ.get('WEBHOOK_PORT', '3000')))

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