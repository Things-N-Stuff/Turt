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
bot = Bot(command_prefix=bot_prefix, 
	description=bot_description,
	status=discord.Status.idle,
	activity=discord.Game(name='Starting...'))

# Setup the Cogs
bot.load_extension("bot.cogs.permissions")
bot.load_extension("bot.cogs.elections")
bot.load_extension("bot.cogs.channels")
bot.load_extension("bot.cogs.bothosting")
bot.load_extension("bot.cogs.database")
bot.load_extension("bot.cogs.discipline")

@bot.event
async def on_ready():
	print("Discord.py " + discord.__version__)
	print(f"{bot.user.name}: {bot.user.id}")
	print("Bot started at " + datetime.now().strftime("%H:%M:%S"))
	await bot.change_presence(status=discord.Status.online, activity=discord.Game(name='Moderating'))
	print("Putting all users in database...")
	bot.sql.setup_database_with_all_users(bot)
	print("Deleting unwanted reactions from elections...")
	await (bot.get_cog("Elections")).delete_unwanted_election_reactions()
	#print("Unbanning those who have served their time...")
	#await (bot.get_cog("Discipline")).checkbans()
	print("Ready!")

@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.errors.NoPrivateMessage): return #Thats expected
	else:
		print(error)
		await ctx.send_help(ctx.command)

#Run the bot
bot.run(bot_token)
