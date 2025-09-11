import customtkinter
import os
from async_tkinter_loop.mixins import AsyncCTk
from config import CONFIG_PATH, setup, config
import webbrowser
import urllib.parse


class BonkyBotConfigApp(customtkinter.CTkToplevel, AsyncCTk):
    def __init__(self):
        super().__init__()
        self.geometry("750x230")
        self.title("Bonky Bot Config")
        self.resizable(False, False)
        self.config_label = customtkinter.CTkLabel(self, text="Twitch", font=("Arial", 20))
        self.config_label.grid(row=0, column=0, padx=(10, 30), pady=5)
        self.twitch_client_id_input = customtkinter.CTkEntry(self, placeholder_text="Client ID", width=200)
        self.twitch_client_id_input.grid(row=1, column=0, padx=(10, 30), pady=(5, 2))
        self.twitch_client_secret_input = customtkinter.CTkEntry(self, placeholder_text="Client Secret", width=200)
        self.twitch_client_secret_input.grid(row=2, column=0, padx=(10, 30), pady=2)
        self.twitch_bot_id_input = customtkinter.CTkEntry(self, placeholder_text="Bot ID", width=200)
        self.twitch_bot_id_input.grid(row=3, column=0, padx=(10, 30), pady=2)
        self.twitch_owner_id_input = customtkinter.CTkEntry(self, placeholder_text="Owner ID", width=200)
        self.twitch_owner_id_input.grid(row=4, column=0, padx=(10, 30), pady=2)
        self.load_config_button = customtkinter.CTkButton(self, text="Load config items", command=self.load_config_items)
        self.load_config_button.grid(row=5, column=0, padx=(10, 30), pady=2)

        self.first_time_config_label = customtkinter.CTkLabel(self, text="Setup", font=("Arial", 20))
        self.first_time_config_label.grid(row=0, column=1, padx=(10, 30), pady=5)

        self.first_time_config_subtitle = customtkinter.CTkLabel(self, text="While logged into your MAIN Twitch account, press these buttons in order", font=("Arial", 15))
        self.first_time_config_subtitle.grid(row=1, column=1, padx=(10, 30), pady=5)

        self.launch_auth_button = customtkinter.CTkButton(self, text="Give bot permissions to moderate actions on your behalf", command=self.authenticate_bot)
        self.launch_auth_button.grid(row=2, column=1, padx=(10, 30))

        self.copy_auth_button = customtkinter.CTkButton(self, text="Give bot permissions to send messages", command=self.copy_bot_auth_url)
        self.copy_auth_button.grid(row=3, column=1, padx=(10, 30))

        self.authenticate_bot_instructions = customtkinter.CTkLabel(self, text="Open a new browser in incognito mode, login to the bot account\n and paste the link into your incognito window", font=("Arial", 15))
        self.authenticate_bot_instructions.grid(row=4, column=1, padx=(10, 30), pady=5)

    def load_config_items(self):
        # Update the config file with the new values if they are not empty
        if self.twitch_client_id_input.get():
            print(f"Updated client ID: {self.twitch_client_id_input.get()}")
            config["Twitch"]["CLIENT_ID"] = self.twitch_client_id_input.get()
        
        if self.twitch_client_secret_input.get():
            print(f"Client Secret: {self.twitch_client_secret_input.get()}")
            config["Twitch"]["CLIENT_SECRET"] = self.twitch_client_secret_input.get()
        
        if self.twitch_bot_id_input.get():
            print(f"Bot ID: {self.twitch_bot_id_input.get()}")
            config["Twitch"]["BOT_ID"] = self.twitch_bot_id_input.get()
        
        if self.twitch_owner_id_input.get():
            print(f"Owner ID: {self.twitch_owner_id_input.get()}")
            config["Twitch"]["OWNER_ID"] = self.twitch_owner_id_input.get()
        
        with open(CONFIG_PATH, "w") as configfile:
            config.write(configfile)


    def authenticate_bot(self):
        # Open the server webpage in the default web browser
        perms = [
            "user:read:follows",
            "channel:bot",
            "channel:read:subscriptions",
            "channel:read:ads",
            "channel:manage:vips",
            "channel:manage:moderators",
            "channel:manage:redemptions",
            "bits:read",
            "moderator:read:chatters",
            "moderator:read:followers",
            "moderator:manage:shoutouts",
            "moderator:manage:banned_users",
            "moderator:manage:announcements",
        ]
        q_string = urllib.parse.quote(" ".join(perms))
        AUTH_URL = f"http://localhost:4343/oauth?scopes={q_string}"
        webbrowser.open_new_tab(AUTH_URL)

    def copy_bot_auth_url(self):
        perms = [
            "user:read:follows",
            "user:read:chat",
            "user:write:chat",
            "user:bot",
            "moderator:read:followers",
            "moderator:manage:announcements",
        ]
        q_string = urllib.parse.quote(" ".join(perms))
        AUTH_URL = f"http://localhost:4343/oauth?scopes={q_string}"
        # Copy the URL to the clipboard
        self.clipboard_clear()
        self.clipboard_append(AUTH_URL)
        self.update()

    def quit_app(self):
        self.quit()
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    setup()
    # customtkinter.set_appearance_mode("dark")
    # customtkinter.set_default_color_theme("blue")

    # Initialize and run the Bonky Bot application
    app = BonkyBotConfigApp()
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.async_mainloop()