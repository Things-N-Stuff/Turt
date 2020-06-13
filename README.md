# Turt

Discord Server Moderation Bot

## Requirements
 - python3
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

Note: Turt bot has been known (rarely) to hang on startup when checking previous elections on some versions of python. If this happens, install python3.6 and run `python3.6 turt.py` instead. I have no clue why this works, but it does for me.

## Plans for Turt

Our current plans for Turt can be seen [here](https://docs.google.com/document/d/1-u4tWmgt2BiIjdiXu1FnjCUi64xBHLHDEhf8N6rCe-g).  
If you wish to contribute to this list, [open an issue](https://github.com/Things-N-Stuff/Turt/issues).

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

- Bot hosting:
	- The following commands can only be called by specific users, which are listed in the config file.
		- It is recommended to only include the bot hoster and a few extremely trusted friends.
	- `./t shutdown` shuts the bot down. Useful in case of an emergency and the bot hoster does not have physical access to the server the bost is hosted on.
	- `./t restart` restarts the bot. Useful for applying updates.
