# Turt

Discord Server Moderation Bot

## Requirements
 - *at least* python3.6
 - [discord.py](https://github.com/Rapptz/discord.py)

## Using the Bot
If you haven't already, clone this repo by running the following command.

```
git clone https://github.com/Things-N-Stuff/Turt
```

You then must set up the local database: `python3 setup.py`

Before you can actually start using the bot, you will need to create your own `config.py`.
The sample config is `config.py.template` and holds all possible configuration options aswell as a comment describing what each is for.

After configuration, just run `python3 turt.py`. 

Note that you might have to either alias `python3=python3.6` (or whichever verion you installed) or just use `python3.6 turt.py` (Note that if this is done, then the restart command will not work).

In order for the restart command to work, the *default* python3 version on your system must be at least python3.6 (aliases don't count). Most systems today come with `python3.7` installed as their default version.

## Plans for Turt

Our current plans for Turt can be seen [here](https://docs.google.com/document/d/1-u4tWmgt2BiIjdiXu1FnjCUi64xBHLHDEhf8N6rCe-g).  
If you wish to contribute to this list, [open an issue](https://github.com/Things-N-Stuff/Turt/issues).

## Server Permissions 

Be very cautious with this, as your server could be raided if the bost hoster modifies the code.

It is recommended to give Turt bot the following server permissions in each server (however you should be skeptical):
- `manage server` - Allows Turt to see all server invites so banned members can be invited back once their ban has expired
    - Additionally, "Members with this permission can change the server's name or move regions". If you do not want this, then do NOT enable this permission for Turt
        - Note that vanilla Turt does not do either or these things (however the bot hoster may have modified the code to raid your server)
    - Without this permission, Turt will be unable to give server invites with ban messages, potentially preventing people from returning to the server after their ban.
- `ban members` - Allows Turt to ban members when they reach a bannable number of severity points in the warning system
    - Note that vanilla Turt will not ban users for any other reason (however the bot hoster may have modified the code to raid your server)
    - Without this permission, Turt will only be able to recommend bans, but will be unable to enforce them or unban people when their temporary ban has expired.
- `manage messages` - Allows Turt to delete other users' messages.
    - This allows for 2 things:
        - Turt can enforce link-only rules in link-only channels (the bot deletes non-link messages)
        - Turt can delete reactions from active election messages that are unrelated to the election
    - Note that bot hosters may have modified the code, allowing the bot hoster to raid your server if this is enabled (Be cautious and skeptical).

## Features

- Elections:
	- Turt can host votes (They are called "elections" because nobody would take "polls" seriously).
	- Elections are not enforced by turt, so they can be about anything (like adding channels, renaming them, or literally electing someone)
	- In order to have an election in a server, a whitelisted user must first configure the election message channel:
		- `./t electionchannel <channel_id>` to configure the election channel (whitelist only)
	- There are two types of elections: 
		- Yes/no elections
			- Users react with either :thumbsup: or :thumbsdown: to vote
			- Example yes/no election: "Should we add a meme channel?"
		- Multi-option elections
			- Users react with a number emoji that matches their choice displayed in the election embed
			- Example multi-option election: "What should we rename the meme channel to?"
				- Options would be within the election embed
	- All reactions that are not related to the election are removed by turt bot
		- This includes number emojis that excede the number of options in a multi-option election
	- All users can call elections with the `./t callvote` command unless the server owner configured it otherwise.
		- Each user can only call an election once every 24 hours, unless whitelisted.
		- `./t allcancallvote <can_all_call_vote>` set whether or not all users will be able to create elections. Whitelisted users are unaffected.
			- `<can_all_call_vote>` must either be "true" or "false"
			- It is recommended to set this to false in public servers.
	- Server owners can call `./t deleteelection <electionid>` in order to delete any election in their server. Useful to prevent trolling.
		- `<electionid>` can be seen on the second field of an election message (next to `Time Left`)

- Channel Moderation:
	- `./t prune <n>` will delete the last `n` number of messages in the current channel (whitelist only)
		- You can only prune up to 99 messages at one time
	- `./t setlinkonly <channel_id> [true/false]` will set a channel's "link-only status" (whitelist only)
		- When a channel is "link-only", only links will be able to be posted in that channel (messages following a link are allowed)
		- If `[true/false]` is not supplied, turt will set the channel to link-only (as if `true` was supplied).
		- The channel must be in the server you are calling the command from.

- General Server Moderation:
	- `./t whitelist <user_id> <true/false>` will set whitelist status for a user for your server
		- Whitelisted users will be allowed to call more potentially destructive commands (specified by `(whitelist only)`)
		- Only server owners can set whitelist status for users within their server.
	- `./t warn <user> <severity> <reason>` will warn a user on a server and add `<severity>` severity points to their account for this server.
		- `<user>` should be an @mention
		- Severity points are specific to each server
		- It is recommended to be lenient with severity points, and repeated offences are recommended to result in increased severity points.
			- It is also recommended for server owners to keep watch over his/her whitelisted users in case they are abusing this command (and warnings could be applied to them)
		- The punishments for reaching each number of severity points is as follows:
			- 10 severity points - Ban for 1 hour
			- 20 severity points - Ban for 1 day
			- 30 severity points - Ban for 1 week
			- Every 10 severity points afterwards results in a ban for 30 days
		- Only server owners can `./t warn` whitelisted users for their server (whitelisted users cannot warn each other).
			- If a whitelisted user sees another whitelisted user abuse his/her power, then the witness should report the incident to the server owner so that he/she can take appropriate action.
		- whitelisted users can warn anyone that is not whitelisted or server owner
		- Users will only be banned by Turt bot if Turt bot has the `ban members` permission on a server and if Turt has a higher role on the role hierarchy than the user it is banning.

- Bot hosting:
	- The following commands can only be called by specific users, which are listed in the config file.
		- It is recommended to only include the bot hoster and a few extremely trusted friends.
	- `./t shutdown` shuts the bot down. Useful in case of an emergency and the bot hoster does not have physical access to the server the bost is hosted on.
	- `./t restart` restarts the bot. Useful for applying updates.
