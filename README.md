# BonkyBot
A custom Twitch bot for the community, built with love by BonkyWonky aka WilfredOwen/Bonksolid.

## Bot Setup

1. Create a new Twitch account. This will be the dedicated bot account.

2. Enter your CLIENT_ID, CLIENT_SECRET, BOT_ID and OWNER_ID into a config file.

3. Run the bot.

4. Open a new browser / incognito mode, log in as the bot account and visit http://localhost:4343/oauth?scopes=user:read:chat%20user:write:chat%20user:bot

5. In your main browser whilst logged in as your account, visit http://localhost:4343/oauth?scopes=channel:bot%20moderator:read:chatters%20channel:manage:moderators%20channel:manage:vips%20moderator:manage:shoutouts%20moderator:manage:banned_users

6. Run the bot.

## Troubleshooting

Database and logs can be found in `%PROGRAMDATA%\BonkyBot\` where there will be a `logs` folder and a `db` folder.

Close the application, archive this folder into a .zip using 7z or Windows zip and send these to @bonksolid on Discord if you need further assistance.