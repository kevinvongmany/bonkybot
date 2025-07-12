import logging.handlers
import customtkinter
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk


import logging
import os
import asqlite
from config import JSON_DB_PATH, LOG_PATH, PROGRAM_DATA_DIR
from db import MiniGameDatabase, UserDatabase
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
        self.geometry("400x600")
        self.iconpath = ImageTk.PhotoImage(file=resource_path("./bb.ico"))
        self.title("BonkyBot")
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)
        self.resizable(False, False)
        self.minigame_db = MiniGameDatabase()
        self.user_db = UserDatabase()
        self.setup_fonts()
        self.create_widgets()

    def setup_fonts(self):
        self.title_font = customtkinter.CTkFont(family="Comic Sans MS", size=30, weight="bold")
        self.main_font = customtkinter.CTkFont(family="Comic Sans MS", size=15, weight="normal")
        self.button_font = customtkinter.CTkFont(family="Comic Sans MS", size=15, weight="bold")
        
    def create_widgets(self):    
        self.title_label = customtkinter.CTkLabel(self, text="BonkyBot", font=self.title_font)
        self.title_label.pack(pady=(20, 5))

        self.autovip_label = customtkinter.CTkLabel(self, text="Auto VIP keyword", font=self.main_font)
        self.autovip_label.pack(pady=10)
        self.autovip_input = customtkinter.CTkEntry(self, placeholder_text="Keyword", width=200, font=self.main_font)
        self.autovip_input.pack(pady=(0,10))
        self.autovip_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_autovip_keyword, font=self.button_font, state="disabled")
        self.autovip_update_button.pack(pady=(0,10))

        self.autoban_label = customtkinter.CTkLabel(self, text="Auto ban keyword", font=self.main_font)
        self.autoban_label.pack(pady=10)
        self.autoban_input = customtkinter.CTkEntry(self, placeholder_text="Keyword", width=200, font=self.main_font)
        self.autoban_input.pack(pady=(0,10))
        self.autoban_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_autoban_keyword, font=self.button_font, state="disabled")
        self.autoban_update_button.pack(pady=(0,10))


        self.timeout_label = customtkinter.CTkLabel(self, text="Timeout duration (secs)", font=self.main_font)
        self.timeout_label.pack(pady=10)
        self.timeout_input = customtkinter.CTkEntry(self, placeholder_text="Duration", width=200, font=self.main_font)
        self.timeout_input.insert(0, str(self.minigame_db.get_timeout_duration()))
        self.timeout_input.pack(pady=(0,10))
        self.timeout_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_timeout_duration, font=self.button_font, state="disabled")
        self.timeout_update_button.pack(pady=(0,10))

        self.culling_mode_switch = customtkinter.CTkSwitch(self, text="Culling Mode", command=self.update_culling_mode, font=self.main_font)
        self.culling_mode_switch.pack(pady=(10,10))
        self.get_culling_mode()

        self.launch_button = customtkinter.CTkButton(self, text="LAUNCH BOT", command=self.launch_bot, font=self.button_font)
        self.launch_button.pack(pady=(30,10))

        self.open_config_button = customtkinter.CTkButton(self, text="CONFIG FOLDER", command=self.open_config, font=self.button_font)
        self.open_config_button.pack(pady=10)

    def launch_bot(self):
        main()
        self.update_autoban_keyword()
        self.update_autovip_keyword()
        self.launch_button.configure(
            fg_color="red", 
            hover_color="brown", 
            text_color="white", 
            text="CLOSE BOT", 
            command=self.quit_app
        )
        self.autovip_update_button.configure(state="normal")
        self.autoban_update_button.configure(state="normal")
        self.timeout_update_button.configure(state="normal")

    def get_culling_mode(self):
        mode = self.minigame_db.get_culling_mode()
        if mode:
            self.culling_mode_switch.select()
        else:
            self.culling_mode_switch.deselect()

    def update_culling_mode(self):
        mode = self.culling_mode_switch.get()
        self.minigame_db.toggle_culling_mode(mode)

    def update_autoban_keyword(self):
        keyword = self.autoban_input.get()
        self.minigame_db.update_ban_keyword(keyword.lower())

    def update_autovip_keyword(self):
        keyword = self.autovip_input.get()
        self.minigame_db.update_vip_keyword(keyword.lower())

    def update_timeout_duration(self):
        try:
            duration = int(self.timeout_input.get())
            if duration < 0:
                raise ValueError("Duration must be a non-negative integer.")
            self.minigame_db.update_timeout_duration(duration)
        except ValueError as e:
            customtkinter.CTkMessageBox.show_error("Invalid Input", f"Please enter a valid timeout duration: {e}")
            return

    def open_config(self):
        # Open the config file in the default text editor
        os.startfile(PROGRAM_DATA_DIR)
    
    def quit_app(self):
        self.quit()
        self.destroy()
        os._exit(0)
        
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
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.async_mainloop()