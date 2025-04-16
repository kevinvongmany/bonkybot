import os 
CLIENT_ID: str = os.environ["CLIENT_ID"] # The CLIENT ID from the Twitch Dev Console
CLIENT_SECRET: str = os.environ["CLIENT_SECRET"] # The CLIENT SECRET from the Twitch Dev Console
BOT_ID = os.environ["BOT_ID"]  # The Account ID of the bot user...
OWNER_ID = os.environ["OWNER_ID"]  # Your personal User ID..

PROGRAM_DATA_DIR = os.path.join(os.environ["PROGRAMDATA"], "BonkyBot")
LOG_PATH = os.path.join(PROGRAM_DATA_DIR, "logs")
JSON_DB_PATH = os.path.join(PROGRAM_DATA_DIR, "db")

USERS_DB = os.path.join(JSON_DB_PATH, "users.json")

def setup() -> None:
    # Create the directories if they do not exist
    os.makedirs(PROGRAM_DATA_DIR, exist_ok=True)
    os.makedirs(LOG_PATH, exist_ok=True)
    os.makedirs(JSON_DB_PATH, exist_ok=True)
    # Create the JSON file if it does not exist
    if not os.path.exists(USERS_DB):
        with open(USERS_DB, "w") as f:
            f.write("{}")  # Initialize with an empty JSON object
