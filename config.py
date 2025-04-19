import os 
import configparser

config = configparser.ConfigParser()

PROGRAM_DATA_DIR = os.path.join(os.environ["PROGRAMDATA"], "BonkyBot")
CONFIG_PATH = os.path.join(PROGRAM_DATA_DIR, "config.ini")
LOG_PATH = os.path.join(PROGRAM_DATA_DIR, "logs")
JSON_DB_PATH = os.path.join(PROGRAM_DATA_DIR, "db")

def setup() -> None:
    # Create the directories if they do not exist

    os.makedirs(PROGRAM_DATA_DIR, exist_ok=True)
    os.makedirs(LOG_PATH, exist_ok=True)
    os.makedirs(JSON_DB_PATH, exist_ok=True)


    # Create the JSON file if it does not exist
    if not os.path.exists(USERS_DB):
        with open(USERS_DB, "w") as f:
            f.write("{}")  # Initialize with an empty JSON object
    if not os.path.exists(BRICK_DB):
        with open(BRICK_DB, "w") as f:
            f.write("{}")
    if not os.path.exists(DICE_DB):
        with open(DICE_DB, "w") as f:
            f.write("{}")
setup()
config.read(CONFIG_PATH)

if not config.has_section("Twitch"):
    config.add_section("Twitch")
    config.set("Twitch", "CLIENT_ID", "")  
    config.set("Twitch", "CLIENT_SECRET", "")  
    config.set("Twitch", "BOT_ID", "") 
    config.set("Twitch", "OWNER_ID", "") 
    with open(CONFIG_PATH, "w") as configfile:
        config.write(configfile)

CLIENT_ID: str = config.get("Twitch", "CLIENT_ID") # The CLIENT ID from the Twitch Dev Console
CLIENT_SECRET: str = config.get("Twitch", "CLIENT_SECRET") # The CLIENT SECRET from the Twitch Dev Console
BOT_ID = config.get("Twitch", "BOT_ID")  # The Account ID of the bot user...
OWNER_ID = config.get("Twitch", "OWNER_ID")  # Your personal User ID..

USERS_DB = os.path.join(JSON_DB_PATH, "users.json")
BRICK_DB = os.path.join(JSON_DB_PATH, "bricks.json")
DICE_DB = os.path.join(JSON_DB_PATH, "dice.json")
