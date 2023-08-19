from flask import Flask
import os
import hvac

app = Flask(__name__)

# Initialize the Vault client
vault_addr = os.environ.get('VAULT_ADDR', 'http://localhost:8200')
vault_token = os.environ.get('VAULT_TOKEN')
client = hvac.Client(url=vault_addr, token=vault_token)

@app.route('/')
def display_secret():
    secret = client.read('secret/data/webapp/config')
    if secret and 'data' in secret and 'data' in secret['data']:
        return f"Username: {secret['data']['data']['username']}, Password: {secret['data']['data']['password']}"
    return "Error retrieving secret from Vault."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
