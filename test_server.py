from flask import Flask, request
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def test():
    logging.info(f"Received {request.method} request")
    logging.info(f"Headers: {dict(request.headers)}")
    logging.info(f"Data: {request.get_data()}")
    return "Server is running!", 200

if __name__ == "__main__":
    logging.info("Starting test server on port 3000...")
    app.run(host='0.0.0.0', port=3000)