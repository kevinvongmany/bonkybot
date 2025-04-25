import requests
import logging

# Set up logging
logger = logging.getLogger(__name__)

class TwitchAPI:
    BASE_URL = "https://api.twitch.tv/helix"
    
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        logger.info("Requesting access token from Twitch API")
        response = requests.post(url, params=params)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.token_expiry = data["expires_in"]
        else:
            raise Exception("Failed to get access token: {}".format(response.text))

    def make_request(self, endpoint, params=None):
        if not self.access_token or not self.token_expiry:
            self.get_access_token()
        
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        logger.info(f"Making request to {url} with params: {params}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 401:  # Unauthorized
            logger.info("Access token expired, refreshing token")
            self.get_access_token()  # Refresh token
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("API request failed: {}".format(response.text))