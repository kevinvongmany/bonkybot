import customtkinter
import asqlite
import os
import sys
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk
from config import JSON_DB_PATH, CONFIG_PATH, setup, config
import webbrowser
from PIL import ImageTk

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class BonkyBotConfigApp(customtkinter.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        self.geometry("750x230")
        self.iconpath = ImageTk.PhotoImage(file=resource_path("./bb.ico"))
        self.title("Bonky Bot Config")
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)
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

        self.launch_config_server = customtkinter.CTkButton(self, text="Load auth server and database", command=self.setup)
        self.launch_config_server.grid(row=2, column=1, padx=(10, 30))

        self.launch_auth_button = customtkinter.CTkButton(self, text="Give bot permissions to moderate actions on your behalf", command=self.open_server_webpage, state="disabled")
        self.launch_auth_button.grid(row=3, column=1, padx=(10, 30))

        self.copy_auth_button = customtkinter.CTkButton(self, text="Give bot permissions to send messages", command=self.copy_bot_auth_url, state="disabled")
        self.copy_auth_button.grid(row=4, column=1, padx=(10, 30))

        self.authenticate_bot_instructions = customtkinter.CTkLabel(self, text="Open a new browser in incognito mode, login to the bot account\n and paste the link into your incognito window", font=("Arial", 15))
        self.authenticate_bot_instructions.grid(row=5, column=1, padx=(10, 30), pady=5)

    @async_handler
    async def setup(self):
        self.launch_config_server.configure(
            text="Server launched",
            fg_color="green",
            state="disabled"
        )
        self.launch_auth_button.configure(state="normal")
        self.copy_auth_button.configure(state="normal")
        try:
            from bot import Bot
            async with asqlite.create_pool(os.path.join(JSON_DB_PATH, "bonkybot.db")) as tdb, Bot(token_database=tdb, configured=False) as bot:
                await bot.setup_database()
                await bot.start()
        except RuntimeError:
            print("Config items haven't been loaded, please restart app before moving over to Setup.")


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
        # Reload the config file to reflect the changes
        print("Config file updated, please close and restart this app for changes to take effect.")


    def open_server_webpage(self):
        # Open the server webpage in the default web browser
        AUTH_URL = "http://localhost:4343/oauth?scopes=channel:bot%20moderator:read:chatters%20channel:manage:moderators%20channel:manage:vips%20moderator:manage:shoutouts%20moderator:manage:banned_users%20moderator:manage:announcements"
        webbrowser.open_new_tab(AUTH_URL)

    def copy_bot_auth_url(self):
        AUTH_URL = "http://localhost:4343/oauth?scopes=user:read:chat%20user:write:chat%20user:bot"
        # Copy the URL to the clipboard
        self.clipboard_clear()
        self.clipboard_append(AUTH_URL)
        self.update()


if __name__ == "__main__":
    setup()
    # customtkinter.set_appearance_mode("dark")
    # customtkinter.set_default_color_theme("blue")

    # Initialize and run the Bonky Bot application
    app = BonkyBotConfigApp()
    app.async_mainloop()