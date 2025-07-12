import logging
import twitchio
import random

from twitchio.ext import commands
from datetime import datetime, timedelta
from config import OWNER_ID, BOT_ID
from db import UserDatabase, BrickGameDatabase, DiceGameDatabase, MiniGameDatabase
from bot import Bot
import re

LOGGER: logging.Logger = logging.getLogger("BonkyBot")

class BotComponent(commands.Component):
    def __init__(self, bot: Bot) -> None:
        # Load database files into memory
        self.user_db = UserDatabase()
        self.brick_db = BrickGameDatabase()
        self.dice_db = DiceGameDatabase()
        self.minigame_db = MiniGameDatabase()
        self.bot = bot

        
    def _has_mod_perms(self, ctx: commands.Context) -> bool:
        if not (ctx.chatter.broadcaster or self.user_db.is_persistent_mod(ctx.chatter.id)):
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
    
    def _pick_random_chatter(self, chatters: dict[str, str]) -> str:
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

    async def check_for_vip_keyword(self, payload: twitchio.ChatMessage) -> None:
        if self.minigame_db.get_vip_game_status() or payload.chatter.vip:
            return
        vip_keyword = self.minigame_db.get_vip_keyword()
        if vip_keyword and vip_keyword in payload.text.lower():
            await payload.broadcaster.add_vip(
                user=payload.chatter.id
            )
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=f"{payload.chatter.mention} just found the VIP word: {vip_keyword}!",
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

    async def cull_user(self, payload: twitchio.ChatMessage, user) -> None:
        if not self.minigame_db.get_culling_mode():
            return
        if not payload.chatter.moderator or payload.chatter.broadcaster:
            return
        if self.user_db.is_persistent_mod(user.get("id")):
            return
        await payload.broadcaster.timeout_user(
            moderator=OWNER_ID, 
            user=payload.chatter.id, 
            duration=self.minigame_db.get_timeout_duration(), 
            reason="It's just business... nothing personal"
        )

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
            await self.cull_user(payload, user)
            await self.check_for_vip_keyword(payload)
            await self.check_for_ban_keyword(payload)


    
    # Broadcaster Commands 
    @commands.command(aliases=["mod", "m", "m0d"])
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
        await ctx.send(f"Granted permamod to {chatter}.")
        try:
            await ctx.broadcaster.remove_vip(
                user=chatter_id
            )
        except twitchio.HTTPException:
            LOGGER.info(f"{chatter} is not a VIP, skipping removal.")
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
        await ctx.send_announcement(f"{target} is an AWESOME streamer! Please give them a follow and check them out at https://twitch.tv/{target}")
    
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
        if self._has_mod_perms(ctx) is False:
            return
        if len(args) < 2:
            await ctx.send("Format: !ar @username <response>")
            return
        chatter = args[0].replace("@", "").lower()
        if not self.user_db.get_user_id_by_name(chatter):
            await ctx.send(f"{chatter} does not exist.")
            return
        self.user_db.append_auto_response(chatter, " ".join(args[1:]))
        await ctx.send(f"Added auto-response for {chatter}: {' '.join(args[1:])}.")

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
            target = self._pick_random_chatter(chatters)
            if target == self.brick_db.get_users_target(ctx.chatter.name):
                target_id = self.user_db.get_user_id_by_name(target)
                if target_id:
                    await ctx.send(f"{ctx.chatter.name} hit their target {target}! They have been timed out!")
                    await ctx.channel.timeout_user(
                        moderator=OWNER_ID, 
                        user=target_id, 
                        duration=self.minigame_db.get_timeout_duration(), 
                        reason="Got bricked"
                        )
                    await ctx.broadcaster.remove_vip(
                        user=target_id
                    )
                    return
        target_id = self.user_db.get_user_id_by_name(target)
        if target_id == BOT_ID:
            LOGGER.info(f"{ctx.chatter.name} tried to brick the bot.")
            await ctx.send(f"{ctx.chatter.name} just threw a brick at {target}!")
            await ctx.broadcaster.timeout_user(
                moderator=OWNER_ID,
                user=ctx.chatter.id,
                duration=self.minigame_db.get_timeout_duration(),
                reason="Tried to brick the bot"
            )
            return

        if ctx.broadcaster.name in target.lower():
            await ctx.send(f"{ctx.chatter.name} just threw a brick at {ctx.broadcaster.name}!")
            await ctx.channel.timeout_user(
                moderator=OWNER_ID, 
                user=ctx.chatter.id, 
                duration=self.minigame_db.get_timeout_duration(), 
                reason="Got bricked"
                )
            await ctx.broadcaster.remove_vip(
                user=ctx.chatter.id
            )
            return
        await ctx.send(self.throw_brick_at_user(ctx.chatter.name, target))

    @commands.cooldown(rate=1, per=5, key=commands.BucketType.chatter)
    @commands.command(aliases=["target"])
    async def brick_target(self, ctx: commands.Context, *args) -> None:
        target = ""
        chatter_name = ctx.chatter.name
        _args = self.clean_args(ctx.args)
        if _args:
            target = _args[0]
        # Set the target for the user...
        if not target:
            await ctx.send(f"{chatter_name} current target : {self.brick_db.get_users_target(chatter_name)}. To change it, use !target <username>.")
            return
        target = target.replace("@", "").lower()
        if self.user_db.get_user_id_by_name(target) == BOT_ID:
            LOGGER.info(f"{chatter_name} tried to set the bot as their target.")
            await ctx.send("You cannot set the bot as your target.")
            ctx.broadcaster.timeout_user(
                moderator=OWNER_ID,
                user=ctx.chatter.id,
                duration=self.minigame_db.get_timeout_duration(),
                reason="Tried to set the bot as their target"
            )
            return
        if target == chatter_name:
            await ctx.send("You cannot set yourself as your target.")
            return
        elif target == ctx.broadcaster.name:
            await ctx.send("You cannot set the streamer as your target.")
            return
        self.brick_db.set_users_target(chatter_name, target)
        await ctx.send(f"Set {target} as your target. !brick them to time them out!")

    @commands.cooldown(rate=1, per=5, key=commands.BucketType.chatter)
    @commands.command(aliases=["d20"])
    async def roll_d20(self, ctx: commands.Context) -> None:
        # Roll a dice with the given number of sides...
        random_dice_roll = random.randint(1, 20)
        if random_dice_roll == 20:
            if self.dice_db.is_new_player(ctx.chatter.name) and not ctx.chatter.moderator:
                await ctx.send(f"{ctx.chatter.mention} just got super lucky and rolled a 20 in their first attempt today! You are now a vip!")
                await ctx.broadcaster.add_vip(
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
            await ctx.broadcaster.remove_vip(
                user=ctx.chatter.id
            )
        else:
            await ctx.send(f"{ctx.chatter.mention} rolls a {random_dice_roll}!")

        self.dice_db.add_player(ctx.chatter.name)

    @commands.cooldown(rate=1, per=5, key=commands.BucketType.chatter)
    @commands.command(aliases=["roll"])
    async def roll_dice(self, ctx: commands.Context, *args) -> None:
        dice_format = r"^(\d+)?d\d+$"
        if not args[0] or not re.match(dice_format, args[0]):
            await ctx.send("Please provide a valid dice format (e.g., 1d20, 2d6).")
            return
        dice_roll = self.clean_args(ctx.args)[0]
        try:
            num_dice, sides = map(str, dice_roll.split("d"))
            if not num_dice:
                num_dice = 1
            num_dice = int(num_dice)
            sides = int(sides)            
            if num_dice <= 0 or sides <= 0:
                await ctx.send("Number of dice and sides must be positive.")
                return
            if num_dice > 100 or sides > 100:
                await ctx.send("Too many dice or sides! Please keep it reasonable (max 100 dice, 100 sides).")
                return
            rolls = [random.randint(1, sides) for _ in range(num_dice)]
            total = sum(rolls)
            await ctx.send(f"{ctx.chatter.mention} rolled a {num_dice}d{sides}: {', '.join(map(str, rolls))} (Total: {total})")
        except ValueError as e:
            print(e)
            await ctx.send("Invalid dice format. Please use the format <number of dice>d<sides> (e.g., 1d20, 2d6).")
            return
    
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