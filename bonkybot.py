import asyncio
import logging
import sqlite3

import asqlite
import twitchio
from twitchio.ext import commands
from twitchio import eventsub
import random

import os
import config
from datetime import datetime
from config import CLIENT_ID, CLIENT_SECRET, BOT_ID, OWNER_ID, LOG_PATH, JSON_DB_PATH, setup
from db import UserDatabase, BrickGameDatabase, DiceGameDatabase

LOGGER: logging.Logger = logging.getLogger("BonkyBot")

user_db = UserDatabase()
brick_db = BrickGameDatabase()
dice_db = DiceGameDatabase()
   

class Bot(commands.Bot):
    def __init__(self, *, token_database: asqlite.Pool, configured: bool = True) -> None:
        self.token_database = token_database
        self.configured = configured
        super().__init__(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
        )

    async def setup_hook(self) -> None:
        if not self.configured:
            return
        # Add our component which contains our commands...
        await self.add_component(BotComponent(self))

        # Subscribe to read chat (event_message) from our channel as the bot...
        # This creates and opens a websocket to Twitch EventSub...
        subscription = eventsub.ChatMessageSubscription(broadcaster_user_id=OWNER_ID, user_id=BOT_ID)
        await self.subscribe_websocket(payload=subscription)

        # Subscribe and listen to when a stream goes live..
        # For this example listen to our own stream...
        subscription = eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        # Store our tokens in a simple SQLite Database when they are authorized...
        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """

        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        LOGGER.info("Added token to the database for user: %s", resp.user_id)
        return resp

    async def load_tokens(self, path: str | None = None) -> None:
        # We don't need to call this manually, it is called in .login() from .start() internally...

        async with self.token_database.acquire() as connection:
            rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        for row in rows:
            await self.add_token(row["token"], row["refresh"])

    async def setup_database(self) -> None:
        # Create our token table, if it doesn't exist..
        create_token_table = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
        async with self.token_database.acquire() as connection:
            await connection.execute(create_token_table)

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)


class BotComponent(commands.Component):
    def __init__(self, bot: Bot):
        # Passing args is not required...
        # We pass bot here as an example...
        self.bot = bot

    
    async def get_current_chatters(self, ctx: commands.Context) -> None:
        chatters = await ctx.broadcaster.fetch_chatters(moderator=OWNER_ID)
        chatters_map = {}
        async for user in chatters.users:
            chatters_map[user.id] = user.name
        LOGGER.info(f"Chatters: {chatters_map}")
        return chatters_map
    
    def pick_random_chatter(self, chatters: dict[str, str]) -> str:
        # Pick a random chatter from the list
        random_chatter = random.choice(list(chatters.values()))
        LOGGER.info(f"Random Chatter: {random_chatter}")
        return random_chatter
    
    def throw_brick_at_user(self, from_user_id: str, to_user_id: str) -> str:
        return f"{from_user_id} threw a brick at {to_user_id}"

    def clean_args(self, args: list[str]) -> list[str]:
        """
        when a user repeats a message using the up arrow key, Twitch's 
        chatbox likes to append a random unicode character to the end 
        of the message for some reason.

        This function removes that character and any whitespace from the
        beginning and end of the message.
        """
        args = [arg.replace(u"\U000E0000", "").replace("@", "").strip() for arg in args]
        return [arg.lower() for arg in args if arg]
    
    
    # We use a listener in our Component to display the messages received.
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")
        user = user_db.get_user(payload.chatter.id)
        if not user or user["name"] != payload.chatter.name:
            user = user_db.update_current_chatter(payload)
        if user['persistent_mod'] and not payload.chatter.moderator: 
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=f"{payload.chatter.mention} you're supposed to be a moderator, but you're not. I will fix that for you!",
            )
            LOGGER.info(f"Granting mod status to {payload.chatter.name}")
            await payload.broadcaster.add_moderator(
                user=payload.chatter.id
            )
            user_db.update_user_data(payload.chatter.id, {"mod": True})
            

    @commands.command(aliases=["mod", "m", "m0d"])
    @commands.is_broadcaster()
    async def grant_mod_status(self, ctx: commands.Context, chatter) -> None:
        if not chatter:
            await ctx.send("Please provide a username to mod.")
            return
        chatter = chatter.replace("@", "").lower()
        chatter_id = user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} is not a valid user. They must have chatted at least once to be a valid target.")
            return
        LOGGER.info(f"Granting mod status to {ctx.chatter.name}")
        await ctx.broadcaster.add_moderator(
            user=chatter_id
        )
        user_db.update_user_data(chatter_id, {"mod": True})

    
    @commands.command(aliases=["permamod", "permam0d", "pm"])
    @commands.is_broadcaster()
    async def grant_perm_mod_status(self, ctx: commands.Context, chatter) -> None:
        if not chatter:
            await ctx.send("Please provide a username to grant permanent mod status to.")
            return
        chatter = chatter.replace("@", "").lower()
        chatter_id = user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} is not a valid user. They must have chatted at least once to be a valid target.")
            return
        user_db.grant_permamod(chatter_id)
        await ctx.send(f"Granted permanent mod status to {chatter}.")
        await ctx.broadcaster.add_moderator(
                user=chatter_id
            )
    
    @commands.command(aliases=["unmod"])
    @commands.is_broadcaster()
    async def revoke_mod_status(self, ctx: commands.Context, chatter) -> None:
        if not chatter:
            await ctx.send("Please provide a username to revoke mod status from.")
            return
        chatter = chatter.replace("@", "").lower()
        chatter_id = user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} is not a valid user. They must have chatted at least once to be a valid target.")
            return
        user_db.revoke_mod_status(chatter_id)
        if ctx.chatter.moderator:
            await ctx.send(f"Revoking mod status from {chatter}")
            await ctx.broadcaster.remove_moderator(
                user=chatter_id
            )


    @commands.command(aliases=["brick"])
    async def brickroulette(self, ctx: commands.Context, *args) -> None:
        target = ""
        _args = self.clean_args(ctx.args)
        if _args:
            LOGGER.info(_args)
            target = " ".join(_args)
        else:
            chatters = await self.get_current_chatters(ctx)
            target = self.pick_random_chatter(chatters)
            if target == brick_db.get_users_target(ctx.chatter.name):
                await ctx.send(f"You hit your target! You gain a point!")
        await ctx.send(self.throw_brick_at_user(ctx.chatter.name, target))
        if target.lower() == ctx.broadcaster.name:
            await ctx.send("You just threw a brick at the streamer! Now you die.")
            await ctx.channel.timeout_user(
                moderator=OWNER_ID, 
                user=ctx.chatter.id, 
                duration=5, 
                reason="Lost brick roulette"
                )
            
    @commands.command(aliases=["target"])
    async def brick_target(self, ctx: commands.Context, *args) -> None:
        target = ""
        _args = self.clean_args(ctx.args)
        if _args:
            target = _args[0]
        # Set the target for the user...
        if not target:
            await ctx.send(f"Your current target is set to: {brick_db.get_users_target(ctx.chatter.name)}")
            return
        target = target.replace("@", "").lower()
        if target == ctx.chatter.name:
            await ctx.send("You cannot set yourself as your target.")
            return
        # chatter_id = user_db.get_user_id_by_name(target)
        # if not chatter_id:
        #     await ctx.send(f"{target} is not a valid user. They must have chatted at least once today to be a valid target.")
        #     return
        brick_db.set_users_target(ctx.chatter.name, target)
        await ctx.send(f"Set {target} as your target.")

    @commands.command(aliases=["d20"])
    async def roll_dice(self, ctx: commands.Context) -> None:
        # Roll a dice with the given number of sides...
        random_dice_roll = random.randint(1, 20)
        if random_dice_roll == 20:
            await ctx.send(f"{ctx.chatter.mention} rolls a natural 20!")
        elif random_dice_roll == 1:
            await ctx.send(f"{ctx.chatter.mention} rolls a 1! CRITICAL FAIL!")
            await ctx.channel.timeout_user(
                moderator=OWNER_ID, 
                user=ctx.chatter.id, 
                duration=5, 
                reason="Rolled a 1"
                )
        else:
            await ctx.send(f"{ctx.chatter.mention} rolls a {random_dice_roll}!")
    
    @commands.command(aliases=["help"])
    async def bonky_help(self, ctx: commands.Context) -> None:
        # Display a list of commands...
        await ctx.send(
            f"Viewer commands: !brick, !d20, !help. Broadcaster commands: !mod/!m/!m0d, !unmod/!um/!unm0d, !permamod/!pm/!permam0d. Please message @bonksolid on discord to report bugs or request features."
        )

    @commands.command(aliases=["commands"])
    async def bonky_commands(self, ctx: commands.Context) -> None:
        # Display a list of commands...
        await ctx.send(
            f"!brick - randomly bricks a random chatter, but times you out if you hit the streamer. !brick <username> - bricks the specified user. !d20 - rolls a d20 and times you out if you roll a 1."
        )

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        await payload.broadcaster.send_message(
            sender=self.bot.bot_id,
            message=f"Hi... {payload.broadcaster}! You are live!",
        )



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

    async def runner() -> None:
        async with asqlite.create_pool(os.path.join(JSON_DB_PATH, "bonkybot.db")) as tdb, Bot(token_database=tdb, configured=False) as bot:
            await bot.setup_database()
            await bot.start()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt...")


if __name__ == "__main__":
    main()