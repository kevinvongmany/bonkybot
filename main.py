import logging.handlers
import customtkinter
from async_tkinter_loop import async_handler
from async_tkinter_loop.mixins import AsyncCTk
import asyncio
from twitchio import eventsub
import logging
import os
import asqlite
from config import JSON_DB_PATH, LOG_PATH, PROGRAM_DATA_DIR, OWNER_ID, BOT_ID
from db import MiniGameDatabase, UserDatabase
import twitchio
from PIL import ImageTk
from streamerbonkhandler import ACTIONS
from bot import Bot

from configui import BonkyBotConfigApp

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
        self.bot = None
        self.is_ready = False
        self.geometry("300x750")
        self.iconpath = ImageTk.PhotoImage(file=resource_path("./bb.ico"))
        self.title("BonkyBot")
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)
        self.resizable(False, False)
        self.minigame_db = MiniGameDatabase()
        self.user_db = UserDatabase()
        self.setup_fonts()
        self.setup_logger()
        self.configure_grid()
        self.create_widgets()
        self.error_window = None
        self.config_window = None
        self.setup_bot()
        self.wait_for_server()

    def configure_grid(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=2)
        self.grid_rowconfigure(4, weight=2)
        self.grid_rowconfigure(5, weight=1)
        self.grid_rowconfigure(6, weight=2)
        self.grid_rowconfigure(7, weight=2)
        self.grid_rowconfigure(8, weight=1)
        self.grid_rowconfigure(9, weight=2)
        self.grid_rowconfigure(10, weight=1)
        self.grid_rowconfigure(11, weight=1)
        self.grid_rowconfigure(12, weight=3)
        self.grid_rowconfigure(13, weight=1)
        self.grid_rowconfigure(14, weight=1)


    def setup_fonts(self):
        self.title_font = customtkinter.CTkFont(family="Comic Sans MS", size=25, weight="bold")
        self.main_font = customtkinter.CTkFont(family="Comic Sans MS", size=15, weight="normal")
        self.button_font = customtkinter.CTkFont(family="Comic Sans MS", size=15, weight="bold")
        
    def create_widgets(self):    
        self.title_label = customtkinter.CTkLabel(self, text="BonkyBot", font=self.title_font)
        self.title_label.grid(row=0, column=0)

        self.autovip_label = customtkinter.CTkLabel(self, text="Auto VIP keyword", font=self.main_font)
        self.autovip_label.grid(row=1, column=0)
        self.autovip_input = customtkinter.CTkEntry(self, placeholder_text="Keyword", width=200, font=self.main_font)
        self.autovip_input.grid(row=2, column=0)
        self.autovip_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_autovip_keyword, font=self.button_font)
        self.autovip_update_button.grid(row=3, column=0)

        self.autoban_label = customtkinter.CTkLabel(self, text="Auto ban keyword", font=self.main_font)
        self.autoban_label.grid(row=4, column=0)
        self.autoban_input = customtkinter.CTkEntry(self, placeholder_text="Keyword", width=200, font=self.main_font)
        self.autoban_input.grid(row=5, column=0)
        self.autoban_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_autoban_keyword, font=self.button_font)
        self.autoban_update_button.grid(row=6, column=0)


        self.timeout_label = customtkinter.CTkLabel(self, text="Timeout duration (secs)", font=self.main_font)
        self.timeout_label.grid(row=7, column=0)
        self.timeout_input = customtkinter.CTkEntry(self, placeholder_text="Duration", width=200, font=self.main_font)
        self.timeout_input.insert(0, str(self.minigame_db.get_timeout_duration()))
        self.timeout_input.grid(row=8, column=0)
        self.timeout_update_button = customtkinter.CTkButton(self, text="Update", command=self.update_timeout_duration, font=self.button_font)
        self.timeout_update_button.grid(row=9, column=0)

        self.culling_mode_switch = customtkinter.CTkSwitch(self, text="Culling Mode", command=self.update_culling_mode, font=self.main_font)
        self.culling_mode_switch.grid(row=10, column=0)
        self.get_culling_mode()

        self.streamerbonk_switch = customtkinter.CTkSwitch(self, text="Streamerbonk", command=self.update_streamerbonk, font=self.main_font, state="disabled")
        self.streamerbonk_switch.grid(row=11, column=0)

        self.launch_button = customtkinter.CTkButton(self, text="LOADING", command=self.launch_bot, font=self.button_font, state="disabled")
        self.launch_button.grid(row=12, column=0)
        
        self.open_config_button = customtkinter.CTkButton(self, text="CONFIG", command=self.open_config, font=self.button_font)
        self.open_config_button.grid(row=13, column=0)

        self.open_config_folder_button = customtkinter.CTkButton(self, text="CONFIG FOLDER", command=self.open_config_folder, font=self.button_font)
        self.open_config_folder_button.grid(row=14, column=0)
        self.init_off_state()

    def init_off_state(self):
        self.launch_button.configure(
            fg_color="green", 
            hover_color="darkgreen", 
            text_color="white", 
            text="LAUNCH" if self.is_ready else "LOADING",
            command=self.launch_bot)
        self.autovip_update_button.configure(state="disabled")
        self.autoban_update_button.configure(state="disabled")
        self.timeout_update_button.configure(state="disabled")

    def init_on_state(self):
        self.launch_button.configure(
            fg_color="red", 
            hover_color="brown", 
            text_color="white", 
            text="STOP BOT", 
            command=self.stop_bot
        )
        self.autovip_update_button.configure(state="normal")
        self.autoban_update_button.configure(state="normal")
        self.timeout_update_button.configure(state="normal")

    def launch_bot(self):
        self.start_bot()
        self.update_autoban_keyword()
        self.update_autovip_keyword()
        self.init_on_state()

    @async_handler
    async def start_bot(self) -> None:
        await self.bot.wait_until_ready()
        await self.bot.load_module("bonkybot")
        await self.bot.multi_subscribe(self.load_subscriptions())

    @async_handler
    async def stop_bot(self) -> None:
        await self.bot.delete_all_eventsub_subscriptions()
        await self.bot.unload_module("bonkybot")
        self.init_off_state()

    def load_subscriptions(self):
        subscriptions = []
        try:
            subscriptions.extend([
                eventsub.ChatMessageSubscription(broadcaster_user_id=OWNER_ID, user_id=BOT_ID),
                eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID),
                eventsub.AdBreakBeginSubscription(broadcaster_user_id=OWNER_ID),
                eventsub.ChannelSubscribeSubscription(broadcaster_user_id=OWNER_ID),
                eventsub.ChannelSubscribeMessageSubscription(broadcaster_user_id=OWNER_ID),
                eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=OWNER_ID),
                eventsub.ChannelFollowSubscription(broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID),
                eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=OWNER_ID),
                eventsub.ChannelBitsUseSubscription(broadcaster_user_id=OWNER_ID),
            ])
        except:
            if self.error_window is None or not self.error_window.winfo_exists():
                self.error_window = ErrorWindow(f"Config hasn't been setup properly, please configure and restart app to continue.")
                self.error_window.title("Not configured")
            self.error_window.focus()
        return subscriptions 

    def get_culling_mode(self):
        mode = self.minigame_db.get_culling_mode()
        if mode:
            self.culling_mode_switch.select()
        else:
            self.culling_mode_switch.deselect()

    def get_streamerbonk_mode(self):
        mode = self.minigame_db.get_streamerbonk()
        if mode:
            self.streamerbonk_switch.select()
        else:
            self.streamerbonk_switch.deselect()
    
    def update_culling_mode(self):
        mode = self.culling_mode_switch.get()

        self.minigame_db.toggle_culling_mode(mode)

    @async_handler
    async def update_streamerbonk(self):
        try:
            mode = self.streamerbonk_switch.get()
            await self.bot.wait_until_ready()
            user = await self.bot.fetch_user(id=OWNER_ID)
            rewards = await user.fetch_custom_rewards(ids=[action["redeem_id"] for action in ACTIONS])
            for reward in rewards:
                await reward.update(enabled=mode)
            self.minigame_db.toggle_streamerbonk(mode)
        except Exception as e:
            print(f"Could not turn on redeems for some reason: {e}")


    def update_autoban_keyword(self):
        keyword = self.autoban_input.get()
        self.minigame_db.update_ban_keyword(keyword.lower())

    def update_autovip_keyword(self):
        keyword = self.autovip_input.get()
        self.minigame_db.update_vip_keyword(keyword.lower())

    def update_timeout_duration(self):
        timeout_duration = self.timeout_input.get()
        try:
            duration = int(timeout_duration)
            if duration < 0:
                raise ValueError("Duration must be a non-negative integer.")
            self.minigame_db.update_timeout_duration(duration)
        except ValueError:
            if self.error_window is None or not self.error_window.winfo_exists():
                self.error_window = ErrorWindow(f"Please enter a valid timeout duration: {timeout_duration}")
                self.error_window.title("Invalid Input")
            self.error_window.focus()


    def open_config(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = BonkyBotConfigApp()
            self.config_window.iconphoto = self.iconphoto
        self.config_window.focus()

    def open_config_folder(self):
        # Open the config file in the default text editor
        os.startfile(PROGRAM_DATA_DIR)
    
    def quit_app(self):
        self.quit()
        self.destroy()
        os._exit(0)
    
    def setup_logger(self) -> None:
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
    async def wait_for_server(self):
        while not self.is_ready:
            self.is_ready = self.bot.ready if self.bot else False
            await asyncio.sleep(1)
        self.launch_button.configure(state="normal", text="LAUNCH")
        self.streamerbonk_switch.configure(state="normal")
        self.get_streamerbonk_mode()
        


    @async_handler
    async def setup_bot(self) -> None:
        async with asqlite.create_pool(os.path.join(JSON_DB_PATH, "bonkybot.db")) as tdb:
            async with Bot() as bot:
                try:
                    self.bot = bot
                    self.bot.token_database = tdb
                    print("is it ready?")
                    await self.bot.setup_database()
                    await self.bot.start()
                    
                except RuntimeError:
                    if self.error_window is None or not self.error_window.winfo_exists():
                        self.error_window = ErrorWindow(f"Config hasn't been setup properly, please configure and restart app to continue.")
                        self.error_window.title("Not configured")
                    self.error_window.focus()

class ErrorWindow(customtkinter.CTkToplevel):
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("500x100")

        self.label = customtkinter.CTkLabel(self, text=message)
        self.label.pack(padx=20, pady=20)
        
# def main() -> None:
#     log_file_handler = logging.handlers.TimedRotatingFileHandler(
#         os.path.join(
#             LOG_PATH, 
#             f"bonkybot.log"
#         ),
#         when="midnight",
#         interval=1,
#         backupCount=7,
#     )
    
#     log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
#     twitchio.utils.setup_logging(handler=log_file_handler, formatter=log_formatter, level=logging.INFO)

#     @async_handler
#     async def runner() -> None:
#         async with asqlite.create_pool(os.path.join(JSON_DB_PATH, "bonkybot.db")) as tdb, Bot(token_database=tdb, 
#                                                                                               bot_component=BotComponent, 
#                                                                                               configured=True, 
#                                                                                               ) as bot:
#             await bot.setup_database()
#             await bot.start()
#     try:
#         runner()
#     except RuntimeError:
#         print("Config items haven't been loaded, please close this app and configure using bonkybotconfig.exe.")

if __name__ == "__main__":
    # Initialize and run the Bonky Bot application
    app = BonkyBotApp()
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.async_mainloop()