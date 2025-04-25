import json
import os
from config import USERS_DB, BRICK_DB, DICE_DB, CLIENT_ID, CLIENT_SECRET
from datetime import datetime
from twitchapi import TwitchAPI

import logging

# Set up logging
logger = logging.getLogger(__name__)

class JSONDatabase:
    """
    A simple class to manage JSON data in a file.
    Expected data format:
    {
        "key": "value",
        "key2": "value2",
        ...
    }
    """

    def __init__(self, filepath, default_data):
        self._filepath = filepath
        _loaded_data = self.load_data()
        self.data = _loaded_data if _loaded_data else default_data
        self.save_data()

    def load_data(self):
        if os.path.exists(self._filepath):
            with open(self._filepath, "r") as f:
                return json.load(f)

    def save_data(self):
        with open(self._filepath, "w") as f:
            json.dump(self.data, f, indent=4)

    def reset_data(self, data):
        self.data = data
        self.save_data()
    
    def get_current_timestamp(self) -> int:
        # Get the current timestamp
        return int(datetime.now().timestamp())

class UserDatabase(JSONDatabase):
    """
    A simple class to manage user data in a JSON file.
    Expected data format:
    {
        "users": [
            {
                "id": "123456789",
                "name": "username",
                "mod": false,
                "sub": false,
                "last_message": "Hello, world!"
            },
            ...
        ]
    }
    """
    DEFAULT_DATA = {
        "users": []
    }

    def __init__(self):
        super().__init__(USERS_DB, self.DEFAULT_DATA)
        self.twitch_api = TwitchAPI(CLIENT_ID, CLIENT_SECRET)

    def add_user(self, user_id, payload):
        self.data["users"].append({
            "id": user_id,
            **payload
        })
        self.save_data()

    def update_user_data(self, user_id, payload):
        for user in self.data["users"]:
            if user["id"] == user_id:
                user.update(payload)
                self.save_data()
                return
        self.add_user(user_id, payload) # if user didn't exist, add it        
        self.save_data()
    
    def update_current_chatter(self, payload):
        # Check if user already exists
        for user in self.data["users"]:
            if user["id"] == payload.chatter.id:
                user["name"] = payload.chatter.name
                user["mod"] = payload.chatter.moderator
                user["sub"] = payload.chatter.subscriber
                user["last_message_ts"] = self.get_current_timestamp()
                self.save_data()
                return user
            
        new_user = {
            "id": payload.chatter.id,
            "name": payload.chatter.name,
            "mod": payload.chatter.moderator,
            "sub": payload.chatter.subscriber,
            "persistent_mod": False,
            "points": 0
        }
        self.data["users"].append(new_user)
        self.save_data()
        return new_user

    def get_user(self, user_id) -> dict[str, str]|None:
        # Check if user exists
        for user in self.data["users"]:
            if user["id"] == user_id:
                return user
        return None
    
    def get_user_id_by_name(self, username) -> str|None:
        # Check if user exists
        for user in self.data["users"]:
            if user["name"] == username:
                return user["id"]
        try:
            user_data = self.twitch_api.make_request("users", params={"login": username})
            user_id = user_data["data"][0]["id"]
            self.update_user_data(user_id, {"name": username})
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to get user ID for {username}: {user_data}. Error: {e}")
            user_id = None
        except Exception as e:
            logger.error(f"Error while fetching user ID for {username}: {e}")
            user_id = None
        return user_id
    
    def grant_permamod(self, user_id) -> None:
        self.update_user_data(user_id, {"mod": True, "persistent_mod": True})

    def revoke_permamod(self, user_id) -> None:
        # Check if user exists
        self.update_user_data(user_id, {"persistent_mod": False})

    def revoke_mod_status(self, user_id) -> None:
        # Check if user exists
        self.update_user_data(user_id, {"mod": False, "persistent_mod": False})

    def append_auto_response(self, username, response) -> None:
        # Check if user exists
        for user in self.data["users"]:
            if user["name"] == username:
                if "auto_responses" not in user:
                    user["auto_responses"] = []
                user["auto_responses"].append(response)
                self.save_data()
    
    def is_supermod(self, user_id) -> bool:
        # Check if user is a supermod
        for user in self.data["users"]:
            if user["id"] == user_id:
                return user.get("supermod", False)
        return False
    


class BrickGameDatabase(JSONDatabase):
    """
    A simple class to manage brick game data in a JSON file.
    Expected data format:
    {
        "default_target": "khan",
        "players": {
            "wilfredowen": {
                "target": "razorxcut"
            },
            .
            .
            .
        }
    }
    """
    DEFAULT_DATA = {
        "default_target": "khan",
        "players": {}
    }

    def __init__(self):
        super().__init__(BRICK_DB, self.DEFAULT_DATA)

    def get_default_target(self):
        return self.data["default_target"]
    
    def set_default_target(self, target):
        self.data["default_target"] = target
        self.save_data()
    
    def get_users_target(self, username):
        if username not in self.data["players"]:
            return self.data["default_target"]
        return self.data["players"][username].get("target", self.data["default_target"])
    
    def set_users_target(self, username, target):
        if username not in self.data["players"]:
            self.data["players"][username] = {}
        self.data["players"][username]["target"] = target
        self.save_data()
    
    def is_target(self, from_user, current_target):
        # Check if input_user is the target of target_user
        target = self.get_users_target(from_user)
        return target.lower() == current_target.lower()
    
class DiceGameDatabase(JSONDatabase):
    """
    A simple class to manage dice game data in a JSON file.
    Expected data format:
    {
        timestamp: 1230912348,
        "players_today": [
            "john",
            "doe"
        ]
    }
    """
    DEFAULT_DATA = {
        "timestamp": 0,
        "players_today": []
    }

    def __init__(self):
        super().__init__(DICE_DB, self.DEFAULT_DATA)
        self.reset_data(self.DEFAULT_DATA)
        self.set_timestamp()

    def get_timestamp(self):
        return self.data["timestamp"]
    
    def set_timestamp(self):
        self.data["timestamp"] = self.get_current_timestamp()
        self.save_data()

    def is_new_player(self, username):
        username = username.lower().strip()
        # Check if user is already in the players_today list
        return username not in self.data["players_today"]
    
    def add_player(self, username):
        username = username.lower().strip()
        # Add user to the players_today list
        if username not in self.data["players_today"]:
            self.data["players_today"].append(username)
            self.save_data()
