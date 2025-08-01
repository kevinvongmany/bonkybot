import json
import os
from config import USERS_DB, BRICK_DB, DICE_DB, MINIGAME_DB, CLIENT_ID, CLIENT_SECRET
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
        if not _loaded_data:
            self.save_data(default_data)


    def load_data(self):
        if os.path.exists(self._filepath):
            with open(self._filepath, "r") as f:
                return json.load(f)

    def save_data(self, data):
        with open(self._filepath, "w") as f:
            json.dump(data, f, indent=4)

    def reset_data(self, data):
        self.save_data(data)
    
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
        data = self.load_data()
        data["users"].append({
            "id": user_id,
            **payload
        })
        self.save_data(data)

    def update_user_data(self, user_id, payload):
        data = self.load_data()
        for user in data["users"]:
            if user["id"] == user_id:
                user.update(payload)
                self.save_data(data)
                return
        self.add_user(user_id, payload) # if user didn't exist, add it        
    
    def update_current_chatter(self, payload):
        data = self.load_data()
        for user in data["users"]:
            if user["id"] == payload.chatter.id:
                user["name"] = payload.chatter.name
                user["last_message_ts"] = self.get_current_timestamp()
                self.save_data(data)
                return user
            
        new_user = {
            "id": payload.chatter.id,
            "name": payload.chatter.name,
            "persistent_mod": False,
            "points": 0
        }
        data["users"].append(new_user)
        self.save_data(data)
        return new_user

    def get_user(self, user_id) -> dict[str, str]|None:
        data = self.load_data()
        for user in data["users"]:
            if user["id"] == user_id:
                return user
        return None
    
    def get_user_id_by_name(self, username) -> str|None:
        data = self.load_data()
        for user in data["users"]:
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
        self.update_user_data(user_id, {"persistent_mod": False})

    def revoke_mod_status(self, user_id) -> None:
        self.update_user_data(user_id, {"mod": False, "persistent_mod": False})

    def append_auto_response(self, username, response) -> None:
        data = self.load_data()
        for user in data["users"]:
            if user["name"] == username:
                if "auto_responses" not in user:
                    user["auto_responses"] = []
                user["auto_responses"].append(response)
                self.save_data(data)
    
    def is_persistent_mod(self, user_id) -> bool:
        data = self.load_data()
        # Check if user is a supermod
        for user in data["users"]:
            if user["id"] == user_id:
                return user.get("persistent_mod", False)
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
        data = self.load_data()
        return data["default_target"]
    
    def set_default_target(self, target):
        data = self.load_data()
        data["default_target"] = target
        self.save_data(data)
    
    def get_users_target(self, username):
        data = self.load_data()
        if username not in data["players"]:
            return data["default_target"]
        return data["players"][username].get("target", data["default_target"])
    
    def set_users_target(self, username, target):
        data = self.load_data()
        if username not in data["players"]:
            data["players"][username] = {}
        data["players"][username]["target"] = target
        self.save_data(data)
    
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
        data = self.load_data()
        return data["timestamp"]
    
    def set_timestamp(self):
        data = self.load_data()
        data["timestamp"] = self.get_current_timestamp()
        self.save_data(data)

    def is_new_player(self, username):
        data = self.load_data()
        username = username.lower().strip()
        # Check if user is already in the players_today list
        return username not in data["players_today"]
    
    def add_player(self, username):
        username = username.lower().strip()
        data = self.load_data()
        # Add user to the players_today list
        if username not in data["players_today"]:
            data["players_today"].append(username)
            self.save_data(data)

class MiniGameDatabase(JSONDatabase):
    """
    A simple class to manage mini game data in a JSON file.
    Expected data format:
    """
    DEFAULT_DATA = {
        "ban_game" : {
            "ban_keyword": "",
            "timeout_duration": 5,
        },
        "vip_game" : {
            "vip_keyword": "",
            "is_found": False
        },
        "mod_game" : {
            "vip_keyword": "",
            "is_found": False
        },
        "culling_mode": False
    }

    def __init__(self):
        super().__init__(MINIGAME_DB, self.DEFAULT_DATA)


    def get_timeout_duration(self):
        data = self.load_data()
        try:
            return data["ban_game"]["timeout_duration"]
        except KeyError:
            return self.DEFAULT_DATA["ban_game"]["timeout_duration"]
    
    def get_ban_keyword(self):
        data = self.load_data()
        try:
            return data["ban_game"]["ban_keyword"]
        except KeyError:
            return self.DEFAULT_DATA["ban_game"]["ban_keyword"]
    
    def get_vip_keyword(self):
        data = self.load_data()
        try:
            return data["vip_game"]["vip_keyword"]
        except KeyError:
            return self.DEFAULT_DATA["vip_game"]["vip_keyword"]
    
    def get_vip_game_status(self):
        data = self.load_data()
        try:
            return data["vip_game"]["is_found"]
        except KeyError:
            return self.DEFAULT_DATA["vip_game"]["is_found"]

    def get_culling_mode(self):
        data = self.load_data()
        try:
            return data["culling_mode"]
        except KeyError:
            return self.DEFAULT_DATA["culling_mode"]

    def update_ban_keyword(self, keyword):
        data = self.load_data()
        try:
            data["ban_game"]["ban_keyword"] = keyword
        except KeyError:
            data["ban_game"] = {"ban_keyword": keyword, "timeout_duration": self.DEFAULT_DATA["ban_game"]["timeout_duration"]}
        self.save_data(data)
    
    def update_vip_keyword(self, keyword):
        data = self.load_data()
        try:
            data["vip_game"]["vip_keyword"] = keyword
            data["vip_game"]["is_found"] = False
        except KeyError:
            data["vip_game"] = {"vip_keyword": keyword, "is_found": False}
        self.save_data(data)

    def update_timeout_duration(self, duration):
        data = self.load_data()
        try:
            data["ban_game"]["timeout_duration"] = duration
        except KeyError:
            data["ban_game"] = {"ban_keyword": self.DEFAULT_DATA["ban_game"]["ban_keyword"], "timeout_duration": duration}
        self.save_data(data)

    def update_vip_game_status(self, status):
        data = self.load_data()
        try:
            data["vip_game"]["is_found"] = status
        except KeyError:
            data["vip_game"] = {"vip_keyword": self.DEFAULT_DATA["vip_game"]["vip_keyword"], "is_found": status}
        self.save_data(data)

    def toggle_culling_mode(self, mode: int = None):
        data = self.load_data()
        data["culling_mode"] = bool(mode)
        self.save_data(data)