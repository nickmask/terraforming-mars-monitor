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
        self.player_id = os.environ.get('PLAYER_ID')
        self.game_age = 22
        self.undo_count = 0
        self.current_waiting_for = None
        
        # WhatsApp credentials from environment variables
        self.whatsapp_token = os.environ.get('WHATSAPP_TOKEN')
        self.whatsapp_phone_id = os.environ.get('WHATSAPP_PHONE_ID')
        self.recipient_phones = os.environ.get('RECIPIENT_PHONES', '').split(',')
        
        # Player name mapping
        self.players = {
            "red": "Tess",
            "blue": "Nick",
            "green": "Katrin",
            "yellow": "Joe"
        }
        
        # Verify configuration
        if not all([self.player_id, self.whatsapp_token, self.whatsapp_phone_id, self.recipient_phones]):
            logging.error("Missing required environment variables!")
            raise ValueError("Missing required environment variables!")
        
        logging.info("Monitor initialized successfully")
        logging.info(f"Player ID: {self.player_id}")
        logging.info(f"Number of recipients: {len(self.recipient_phones)}")
    
    def get_player_name(self, color):
        """Convert color to player name"""
        return self.players.get(color.lower(), color)

    def send_whatsapp_message(self, message):
        """Send a WhatsApp message to all recipients"""
        url = f"https://graph.facebook.com/v21.0/{self.whatsapp_phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json"
        }
        
        for phone in self.recipient_phones:
            phone = phone.strip()
            if not phone:
                continue
                
            data = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            try:
                logging.info(f"Sending WhatsApp message to: {phone}")
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    logging.info(f"Message sent successfully to {phone}: {message}")
                else:
                    logging.error(f"Failed to send to {phone}: {response.status_code}")
                    logging.error(f"Error: {response.text}")
            except Exception as e:
                logging.error(f"Error sending to {phone}: {e}")
        
    def check_waiting_for(self):
        """Check who the game is waiting for"""
        url = f"{self.base_url}/api/waitingfor"
        params = {
            "id": self.player_id,
            "gameAge": self.game_age,
            "undoCount": self.undo_count
        }
        
        try:
            response = requests.get(url, params=params, timeout=65)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error fetching game state: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            return None
        except Exception as e:
            logging.error(f"Error checking game state: {e}")
            return None

    def run(self):
        """Main monitoring loop"""
        logging.info("Starting Terraforming Mars game monitor...")
        
        # Send startup message
        self.send_whatsapp_message("🎮 Terraforming Mars monitor is now active!")
        
        while True:
            try:
                data = self.check_waiting_for()
                
                if data:
                    if 'gameAge' in data:
                        self.game_age = data['gameAge']
                    
                    waiting_for = data.get('waitingFor', [])
                    
                    if waiting_for != self.current_waiting_for:
                        if waiting_for:
                            if len(waiting_for) > 1:
                                message = "🔬 Time for research!"
                            else:
                                name = self.get_player_name(waiting_for[0])
                                message = f"🎮 It's {name}'s turn!"
                            
                            self.send_whatsapp_message(message)
                            
                        self.current_waiting_for = waiting_for
                
            except Exception as e:
                logging.error(f"Error in monitor loop: {e}")
            
            time.sleep(5)  # Wait 5 seconds before next check

if __name__ == "__main__":
    while True:
        try:
            monitor = TerraformingMarsMonitor()
            monitor.run()
        except Exception as e:
            logging.error(f"Fatal error: {e}")
            logging.info("Restarting monitor in 60 seconds...")
            time.sleep(60)
            