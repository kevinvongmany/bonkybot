import customtkinter
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk


import logging
import config
import os
from datetime import datetime
import asqlite
from config import JSON_DB_PATH, LOG_PATH, PROGRAM_DATA_DIR
import twitchio

from bot import Bot
from bonkybot import BotComponent


class BonkyBotApp(customtkinter.CTk, AsyncCTk):
    def __init__(self):
        super().__init__()
        self.geometry("300x150")
        self.title("Bonky Bot App")
        self.config_label = customtkinter.CTkLabel(self, text="Bonky Bot", font=("Arial", 20))
        self.config_label.pack(pady=10)

        self.launch_button = customtkinter.CTkButton(self, text="Launch Bonky Bot", command=self.launch_bot)
        self.launch_button.pack(pady=10)

        self.open_config_button = customtkinter.CTkButton(self, text="Open config and log folder", command=self.open_config)
        self.open_config_button.pack(pady=10)

    def launch_bot(self):
        main()
        self.launch_button.configure(
            fg_color="red", 
            hover_color="brown", 
            text_color="black", 
            text="Close Bot", 
            command=self.quit_app
        )

    def open_config(self):
        # Open the config file in the default text editor
        os.startfile(PROGRAM_DATA_DIR)
    
    def quit_app(self):
        self.quit()
        self.destroy()
        
def main() -> None:
    config.setup()
    log_file_handler = logging.FileHandler(
        os.path.join(
            LOG_PATH, 
            f"bonkybot_{datetime.now().strftime('%Y%m%d')}.log"
        )
    )
    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    twitchio.utils.setup_logging(handler=log_file_handler, formatter=log_formatter, level=logging.INFO)

    @async_handler
    async def runner() -> None:
        async with asqlite.create_pool(os.path.join(JSON_DB_PATH, "bonkybot.db")) as tdb, Bot(token_database=tdb, bot_component=BotComponent, configured=True) as bot:
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