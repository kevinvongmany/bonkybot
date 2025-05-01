import logging.handlers
import customtkinter
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk


import logging
import os
import asqlite
from config import JSON_DB_PATH, LOG_PATH, PROGRAM_DATA_DIR
from db import MiniGameDatabase
import twitchio
from PIL import ImageTk

from bot import Bot
from bonkybot import BotComponent

import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class BonkyBotApp(customtkinter.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        self.geometry("300x450")
        self.iconpath = ImageTk.PhotoImage(file=resource_path("./bb.ico"))
        self.title("Bonky Bot")
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)
        self.resizable(False, False)
        self.minigame_db = MiniGameDatabase()
        self.title_font = customtkinter.CTkFont(family="Roboto", size=35)
        self.main_font = customtkinter.CTkFont(family="Roboto", size=15)
        self.title_label = customtkinter.CTkLabel(self, text="Bonky Bot", font=self.title_font)
        self.title_label.pack(pady=(20, 5))

        self.autoban_label = customtkinter.CTkLabel(self, text="Auto ban keyword", font=self.main_font)
        self.autoban_label.pack(pady=10)
        self.autoban_input = customtkinter.CTkEntry(self, placeholder_text="Keyword", width=200, font=self.main_font)
        self.autoban_input.pack(pady=(0,10))
        self.autoban_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_autoban_keyword, font=self.main_font, state="disabled")
        self.autoban_update_button.pack(pady=(0,10))

        self.automod_label = customtkinter.CTkLabel(self, text="Auto mod keyword", font=self.main_font)
        self.automod_label.pack(pady=10)
        self.automod_input = customtkinter.CTkEntry(self, placeholder_text="Keyword", width=200, font=self.main_font)
        self.automod_input.pack(pady=(0,10))
        self.automod_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_automod_keyword, font=self.main_font, state="disabled")
        self.automod_update_button.pack(pady=(0,10))


        self.launch_button = customtkinter.CTkButton(self, text="LAUNCH BOT", command=self.launch_bot, font=self.main_font)
        self.launch_button.pack(pady=(30,10))

        self.open_config_button = customtkinter.CTkButton(self, text="CONFIG FOLDER", command=self.open_config, font=self.main_font)
        self.open_config_button.pack(pady=10)

    def launch_bot(self):
        main()
        self.update_autoban_keyword()
        self.update_automod_keyword()
        self.launch_button.configure(
            fg_color="red", 
            hover_color="brown", 
            text_color="white", 
            text="CLOSE BOT", 
            command=self.quit_app
        )
        self.autoban_update_button.configure(state="normal")
        self.automod_update_button.configure(state="normal")


    def update_autoban_keyword(self):
        keyword = self.autoban_input.get()
        self.minigame_db.update_ban_keyword(keyword)

    def update_automod_keyword(self):
        keyword = self.automod_input.get()
        self.minigame_db.update_mod_keyword(keyword)

    def open_config(self):
        # Open the config file in the default text editor
        os.startfile(PROGRAM_DATA_DIR)
    
    def quit_app(self):
        self.quit()
        self.destroy()
        
def main() -> None:
    log_file_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(
            LOG_PATH, 
            f"bonkybot.log"
        ),
        when="midnight",
        interval=1,
        backupCount=7,
    )
    
    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    twitchio.utils.setup_logging(handler=log_file_handler, formatter=log_formatter, level=logging.INFO)

    @async_handler
    async def runner() -> None:
        async with asqlite.create_pool(os.path.join(JSON_DB_PATH, "bonkybot.db")) as tdb, Bot(token_database=tdb, 
                                                                                              bot_component=BotComponent, 
                                                                                              configured=True, 
                                                                                              ) as bot:
            await bot.setup_database()
            await bot.start()
    try:
        runner()
    except RuntimeError:
        print("Config items haven't been loaded, please close this app and configure using bonkybotconfig.exe.")

if __name__ == "__main__":
    # Initialize and run the Bonky Bot application
    app = BonkyBotApp()
    app.async_mainloop()