import logging
import twitchio
import random

from twitchio.ext import commands
from datetime import datetime, timedelta
from config import OWNER_ID
from db import UserDatabase, BrickGameDatabase, DiceGameDatabase, MiniGameDatabase
from bot import Bot

LOGGER: logging.Logger = logging.getLogger("BonkyBot")

class BotComponent(commands.Component):
    def __init__(self, bot: Bot) -> None:
        # Load database files into memory
        self.user_db = UserDatabase()
        self.brick_db = BrickGameDatabase()
        self.dice_db = DiceGameDatabase()
        self.minigame_db = MiniGameDatabase()
        self.bot = bot

    
    def _set_supermod(self, user: dict[str, str]) -> None:
        if not user.get("supermod"):
            self.user_db.update_user_data(user["id"], {"supermod": True, "persistent_mod": True})
            LOGGER.info(f"Granting supermod status to {user['name']}")
    
    def _has_super_permissions(self, ctx: commands.Context) -> bool:
        if not (ctx.chatter.broadcaster or self.user_db.is_supermod(ctx.chatter.id)):
            LOGGER.info(f"{ctx.chatter.name} lacks permissions to run this command.")
            return False
        return True

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
    
    def load_user_from_db(self, payload: twitchio.ChatMessage) -> dict[str, str]:
        user = self.user_db.get_user(payload.chatter.id)
        if not user or user["name"] != payload.chatter.name:
            user = self.user_db.update_current_chatter(payload)
        return user
    
    async def check_for_ban_keyword(self, payload: twitchio.ChatMessage) -> None:
        ban_keyword = self.minigame_db.get_ban_keyword()
        if ban_keyword and ban_keyword in payload.text.lower():
            await payload.broadcaster.timeout_user(
                moderator=OWNER_ID, 
                user=payload.chatter.id, 
                duration=self.minigame_db.get_timeout_duration(), 
                reason="Culled for using the forbidden keyword"
            )
            LOGGER.info(f"Timed out moderator {payload.chatter.name} for using the keyword '{ban_keyword}'")

    async def check_for_mod_keyword(self, payload: twitchio.ChatMessage) -> None:
        if self.minigame_db.get_mod_game_status() or payload.chatter.moderator:
            return
        mod_keyword = self.minigame_db.get_mod_keyword()
        if mod_keyword and mod_keyword in payload.text.lower():
            await payload.broadcaster.add_moderator(
                user=payload.chatter.id
            )
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=f"{payload.chatter.mention} has been granted mod status for finding the keyword '{mod_keyword}'!",
            )
            self.user_db.update_user_data(payload.chatter.id, {"mod": True})
            self.minigame_db.update_mod_game_status(True)
    
    async def check_for_mod_status(self, payload: twitchio.ChatMessage, user: dict[str, str]) -> None:
        if user['persistent_mod'] and not payload.chatter.moderator: 
            LOGGER.info(f"Granting mod status to {payload.chatter.name}")
            await payload.broadcaster.add_moderator(
                user=payload.chatter.id
            )
            self.user_db.update_user_data(payload.chatter.id, {"mod": True})

    async def send_auto_response(self, payload: twitchio.ChatMessage, user: dict[str, str]) -> None:
        try:
            if (responses:=user.get("auto_responses")):
                last_msg_dt = datetime.fromtimestamp(user.get("last_message_ts"))
                if datetime.now() - last_msg_dt < timedelta(minutes=10):
                    return
                random_message = random.choice(responses)
                await payload.broadcaster.send_message(
                    sender=self.bot.bot_id,
                    message=f"{payload.chatter.mention} {random_message}",
                )
        finally:
            user['last_message_ts'] = self.user_db.get_current_timestamp()
            self.user_db.update_user_data(payload.chatter.id, user)
    

    # Message events
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        # display all messages in the terminal
        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        print(f"[{timestamp}] [{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")
        if(payload.source_broadcaster == None or payload.source_broadcaster.id == OWNER_ID): # stops bot from moderating other channels (shared chat workaround)
            user = self.load_user_from_db(payload)
            await self.check_for_mod_status(payload, user)
            await self.send_auto_response(payload, user)
            await self.check_for_mod_keyword(payload)
            await self.check_for_ban_keyword(payload)


    
    # Broadcaster Commands 
    @commands.command(aliases=["mod", "m", "m0d"])
    async def grant_mod_status(self, ctx: commands.Context, chatter) -> None:
        if self._has_super_permissions(ctx) is False:
            return
        if not chatter:
            await ctx.send("Please provide a username to mod.")
            return
        chatter = chatter.replace("@", "").lower()
        chatter_id = self.user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} does not exist.")
            return
        LOGGER.info(f"Granting mod status to {ctx.chatter.name}")
        await ctx.broadcaster.add_moderator(
            user=chatter_id
        )
        self.user_db.update_user_data(chatter_id, {"mod": True})
    
    @commands.command(aliases=["permamod", "permam0d", "pm"])
    @commands.is_broadcaster()
    async def grant_perm_mod_status(self, ctx: commands.Context, chatter) -> None:
        if not chatter:
            await ctx.send("Please provide a username to grant permanent mod status to.")
            return
        chatter = chatter.replace("@", "").lower()
        chatter_id = self.user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} does not exist.")
            return
        self.user_db.grant_permamod(chatter_id)
        await ctx.send(f"Granted permanent mod status to {chatter}.")
        await ctx.broadcaster.add_moderator(
                user=chatter_id
            )
        
    @commands.command(aliases=["supermod", "superm0d", "sm"])
    @commands.is_broadcaster()
    async def grant_super_mod_status(self, ctx: commands.Context, chatter) -> None:
        if not chatter:
            await ctx.send("Please provide a username to grant supermod status to.")
            return
        chatter = chatter.replace("@", "").lower()
        chatter_id = self.user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} does not exist.")
            return
        self.user_db.grant_permamod(chatter_id)
        self._set_supermod(self.user_db.get_user(chatter_id))
        await ctx.send(f"Granted super mod status to {chatter}.")
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
        chatter_id = self.user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} does not exist.")
            return
        self.user_db.revoke_mod_status(chatter_id)
        if ctx.chatter.moderator:
            await ctx.send(f"Revoking mod status from {chatter}")
            await ctx.broadcaster.remove_moderator(
                user=chatter_id
            )

    @commands.command(aliases=["so"])
    @commands.is_moderator()
    async def shoutout(self, ctx: commands.Context, *args) -> None:
        if not args:
            await ctx.send("Please provide a username to shoutout.")
            return
        target = self.clean_args(ctx.args)[0]
        target_id = self.user_db.get_user_id_by_name(target)
        if not target_id:
            await ctx.send(f"{target} does not exist.")
            return
        await ctx.send_announcement(f"{target} is an AWESOME streamer! Please give them a follow and check them out at https://www.twitch.tv/{target}")
        await ctx.broadcaster.send_shoutout(
            to_broadcaster=target_id,
            moderator=ctx.chatter.id
        )
    
    @commands.is_elevated()
    @commands.command(aliases=["vip"])
    async def grant_vip_status(self, ctx: commands.Context, chatter) -> None:
        if not chatter:
            await ctx.send("Please provide a username to grant VIP status to.")
            return
        chatter = chatter.replace("@", "").lower()
        chatter_id = self.user_db.get_user_id_by_name(chatter)
        if not chatter_id:
            await ctx.send(f"{chatter} does not exist.")
            return
        await ctx.broadcaster.add_vip(
            user=chatter_id
        )

    @commands.command(aliases=["autoresponse", "ar"])
    async def set_auto_response(self, ctx: commands.Context, *args) -> None:
        if self._has_super_permissions(ctx) is False:
            return
        if len(args) < 2:
            await ctx.send("Please provide a username and an auto response for their first message in chat! Format: !ar @username <response>")
            return
        chatter = args[0].replace("@", "").lower()
        if not self.user_db.get_user_id_by_name(chatter):
            await ctx.send(f"{chatter} does not exist.")
            return
        self.user_db.append_auto_response(chatter, " ".join(args[1:]))
        await ctx.send(f"Added response '{' '.join(args[1:])}' for {chatter}.")

    # Chatter commands 
    @commands.cooldown(rate=1, per=5, key=commands.BucketType.chatter)
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
            if target == self.brick_db.get_users_target(ctx.chatter.name):
                target_id = self.user_db.get_user_id_by_name(target)
                if target_id:
                    await ctx.send(f"{ctx.chatter.name} hit their target {target}! They have been timed out!")
                    await ctx.channel.timeout_user(
                        moderator=OWNER_ID, 
                        user=target_id, 
                        duration=self.minigame_db.get_timeout_duration(), 
                        reason="Brick roulette victim"
                        )
                    return
        if ctx.broadcaster.name in target.lower():
            await ctx.send(f"{ctx.chatter.name} just threw a brick at {ctx.broadcaster.name} and will now be timed out!")
            await ctx.channel.timeout_user(
                moderator=OWNER_ID, 
                user=ctx.chatter.id, 
                duration=self.minigame_db.get_timeout_duration(), 
                reason="Lost brick roulette"
                )
            return
        await ctx.send(self.throw_brick_at_user(ctx.chatter.name, target))

    @commands.cooldown(rate=1, per=5, key=commands.BucketType.chatter)
    @commands.command(aliases=["target"])
    async def brick_target(self, ctx: commands.Context, *args) -> None:
        target = ""
        _args = self.clean_args(ctx.args)
        if _args:
            target = _args[0]
        # Set the target for the user...
        if not target:
            await ctx.send(f"Your current target is set to: {self.brick_db.get_users_target(ctx.chatter.name)}. To change it, use !brick target <username>.")
            return
        target = target.replace("@", "").lower()
        if target == ctx.chatter.name:
            await ctx.send("You cannot set yourself as your target.")
            return
        elif target == ctx.broadcaster.name:
            await ctx.send("You cannot set the streamer as your target.")
            return
        self.brick_db.set_users_target(ctx.chatter.name, target)
        await ctx.send(f"Set {target} as your target. !brick them to get them timed out!")

    @commands.cooldown(rate=1, per=5, key=commands.BucketType.chatter)
    @commands.command(aliases=["d20"])
    async def roll_dice(self, ctx: commands.Context) -> None:
        # Roll a dice with the given number of sides...
        random_dice_roll = random.randint(1, 20)
        if random_dice_roll == 20:
            if self.dice_db.is_new_player(ctx.chatter.name) and not ctx.chatter.moderator:
                await ctx.send(f"{ctx.chatter.mention} just got super lucky and rolled a 20 in their first attempt today! You are now a mod!")
                await ctx.broadcaster.add_moderator(
                    user=ctx.chatter.id
                )
            else:
                await ctx.send(f"{ctx.chatter.mention} rolls a natural 20!")
        elif random_dice_roll == 1:
            await ctx.send(f"{ctx.chatter.mention} rolls a 1! CRITICAL FAIL!")
            await ctx.channel.timeout_user(
                moderator=OWNER_ID, 
                user=ctx.chatter.id, 
                duration=self.minigame_db.get_timeout_duration(), 
                reason="Rolled a 1"
                )
        else:
            await ctx.send(f"{ctx.chatter.mention} rolls a {random_dice_roll}!")

        self.dice_db.add_player(ctx.chatter.name)

    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    @commands.command(aliases=["time", "currenttime"])
    async def get_current_time(self, ctx: commands.Context) -> None:
        current_time = datetime.now().strftime("%I:%M%p")
        await ctx.send(f"The time is currently {current_time} for {ctx.broadcaster.name}")
    
    @commands.cooldown(rate=1, per=60, key=commands.BucketType.chatter)
    @commands.command(aliases=["help"])
    async def bonky_help(self, ctx: commands.Context) -> None:
        # Display a list of commands...
        await ctx.send(
            f"Viewer commands: !brick, !d20, !help. Broadcaster commands: !mod/!m/!m0d, !unmod/!um/!unm0d, !permamod/!pm/!permam0d. Please message @bonksolid on discord to report bugs or request features."
        )

    @commands.cooldown(rate=1, per=60, key=commands.BucketType.chatter)
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
            message=f"{payload.broadcaster} has gone live!",
        )

    @commands.Component.listener("follow")
    async def event_new_follower(self, payload: twitchio.ChannelFollow) -> None:

        # Event dispatched when a user follows the channel from the subscription we made above...

        await payload.broadcaster.send_message(
            sender=self.bot.bot_id,
            message=f"Thanks for the follow {payload.user.name}!",
        )

    @commands.Component.listener("subscription")
    async def event_new_subscription(self, payload: twitchio.ChannelSubscribe) -> None:

        # Event dispatched when a user subscribes to the channel from the subscription we made above...

        await payload.broadcaster.send_message(
            sender=self.bot.bot_id,
            message=f"Thanks for subscribing {payload.user.name}!",
        )

    @commands.Component.listener("ad_break")
    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:

        # Event dispatched when an ad break begins from the subscription we made above...

        await payload.broadcaster.send_announcement(
            sender=self.bot.bot_id,
            message=f"An ad break has started to help keep the channel going, we promise to be back shortly! Stay tuned for more content from {payload.broadcaster.name}! Please consider using twitch.tv/subs/{payload.broadcaster.name} you can skip ads and continue supporting the channel!",
        )
    
# if __name__ == "__main__":
#     main()