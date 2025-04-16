import json
import os
from config import USERS_DB

class User:
    def __init__(self, user_id, name, mod, sub, last_message):
        self.id = user_id
        self.name = name
        self.mod = mod
        self.sub = sub
        self.last_message = last_message

    def __repr__(self):
        return f"User(id={self.id}, name={self.name}, mod={self.mod}, sub={self.sub}, last_message={self.last_message})"

class UserDatabase:
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

    def __init__(self):
        self._filepath = USERS_DB
        self.users = self.load_user_data()

    def load_user_data(self):
        if os.path.exists(self._filepath):
            with open(self._filepath, "r") as f:
                return json.load(f)
        else:
            return {"users": []}
    def save_user_data(self):
        with open(self._filepath, "w") as f:
            json.dump(self.users, f, indent=4)
    
    def update_user(self, payload):
        # Check if user already exists
        for user in self.users["users"]:
            if user["id"] == payload.chatter.id:
                user["name"] = payload.chatter.name
                user["mod"] = payload.chatter.moderator
                user["sub"] = payload.chatter.subscriber
                self.save_user_data()
                return user
            
        new_user = {
            "id": payload.chatter.id,
            "name": payload.chatter.name,
            "mod": payload.chatter.moderator,
            "sub": payload.chatter.subscriber,
            "persistent_mod": False,
            "points": 0
        }
        self.users["users"].append(new_user)
        self.save_user_data()
        return new_user

    def get_user(self, user_id) -> dict[str, str]|None:
        # Check if user exists
        for user in self.users["users"]:
            if user["id"] == user_id:
                return user
        return None
    
    def get_user_id_by_name(self, username) -> str|None:
        # Check if user exists
        for user in self.users["users"]:
            if user["name"] == username:
                return user["id"]
        return None
    
    def grant_permamod(self, user_id) -> None:
        # Check if user exists
        for user in self.users["users"]:
            if user["id"] == user_id:
                user["mod"] = True
                user["persistent_mod"] = True
                self.save_user_data()

    def revoke_mod_status(self, user_id) -> None:
        # Check if user exists
        for user in self.users["users"]:
            if user["id"] == user_id:
                user["mod"] = False
                user["persistent_mod"] = False
                self.save_user_data()