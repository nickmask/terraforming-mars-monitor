import requests
import time
from datetime import datetime
import os
import logging
import sys

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
        
        # Verify configuration
        if not all([self.whatsapp_token, self.whatsapp_phone_id]):
            logging.error("Missing required WhatsApp environment variables!")
            raise ValueError("Missing required WhatsApp environment variables!")
            
        # Log which phone numbers are configured
        logging.info("Configured phone numbers:")
        for player, phone in self.player_phones.items():
            if phone:
                logging.info(f"{player}: Configured")
            else:
                logging.warning(f"{player}: Missing phone number")

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

    def run(self):
        """Main monitoring loop"""
        logging.info("Starting Terraforming Mars game monitor...")
        logging.info(f"Monitoring game ID: {self.game_id}")
        
        # Send startup message to all players
        startup_message = "🎮 Terraforming Mars monitor is now active!"
        for phone in self.player_phones.values():
            if phone:  # Only send if phone number is configured
                self.send_whatsapp_message(phone, startup_message)
        
        while True:
            try:
                game_state = self.get_game_state()
                self.notify_players(game_state)
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logging.error(f"Error in monitor loop: {e}")
                time.sleep(5)

def main():
    try:
        monitor = TerraformingMarsMonitor()
        monitor.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()