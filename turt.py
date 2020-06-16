# import modules
from bot.bot import Bot
import bot.constants as constants

# import discord.py api wrapper
import discord
from discord.ext import commands, tasks

# import python utility libraries
import os
import sys
from datetime import datetime

from bot import constants

tabs

# Import the configuration
try:
    from config import bot_token, bot_prefix, bot_description, shutdown_admins, bot_user_id
except Exception as e:
    print(e)
    print("Turt bot is not configured. In order to run the bot, Turt must be configured in the config.py.template file.")
    exit(-1)

# Determine if the bot has been setup
if not os.path.isfile(constants.db_file):
    print("Turt bot has not been setup. Setup turt bot by running `python3 setup.py`")
    sys.exit(-2)
		


# Turt instance
constants.bot = Bot(command_prefix=bot_prefix, 
    description=bot_description,
    status=discord.Status.idle,
    activity=discord.Game(name='Starting...'))

# Setup the Cogs
constants.bot.load_extension("bot.cogs.permissions")
constants.bot.load_extension("bot.cogs.elections")
constants.bot.load_extension("bot.cogs.channels")
constants.bot.load_extension("bot.cogs.bothosting")
constants.bot.load_extension("bot.cogs.database")
constants.bot.load_extension("bot.cogs.discipline")

@constants.bot.event
async def on_ready():
    print("Discord.py " + discord.__version__)
    print(f"{constants.bot.user.name}: {constants.bot.user.id}")
    print("Bot started at " + datetime.now().strftime("%H:%M:%S"))
    await constants.bot.change_presence(status=discord.Status.online, activity=discord.Game(name='Moderating'))
    print("Putting all users in database...")
    constants.bot.sql.setup_database_with_all_users(constants.bot)
    print("Deleting unwanted reactions from elections...")
    await (constants.bot.get_cog("Elections")).delete_unwanted_election_reactions()
    print("Ready!")

@constants.bot.event
async def on_command_error(ctx, error):
    print(error)
    if isinstance(error, commands.errors.CheckFailure): return #Thats expected
    if isinstance(error, commands.errors.NoPrivateMessage): return #Thats expected
    else:
    	print(error)
    	await ctx.send_help(ctx.command)

#Run the bot
constants.bot.run(bot_token)
