import asqlite
import sqlite3
import twitchio
from twitchio.ext import commands
from twitchio import eventsub
import logging
from config import CLIENT_ID, CLIENT_SECRET, BOT_ID, OWNER_ID

LOGGER: logging.Logger = logging.getLogger("BotLaunch")

class Bot(commands.Bot):
    def __init__(self, *, token_database: asqlite.Pool, bot_component=None, configured: bool = True, ban_keyword: str = "", mod_keyword: str = "") -> None:
        self.bot_component = bot_component
        self.token_database = token_database
        self.configured = configured
        self.ban_keyword = ban_keyword
        self.mod_keyword = mod_keyword
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
        await self.add_component(self.bot_component(self, ban_keyword=self.ban_keyword, mod_keyword=self.mod_keyword))

        # Subscribe to read chat (event_message) from our channel as the bot...
        # This creates and opens a websocket to Twitch EventSub...
        subscription = eventsub.ChatMessageSubscription(broadcaster_user_id=OWNER_ID, user_id=BOT_ID)
        await self.subscribe_websocket(payload=subscription)

        # Subscribe and listen to when a stream goes live..
        # For this example listen to our own stream...
        subscription = eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.AdBreakBeginSubscription(broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.ChannelSubscribeSubscription(broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.ChannelFollowSubscription(broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID)
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