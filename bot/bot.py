
# import modules
from bot.util import sql
from bot.cogs import permissions
from bot.cogs import elections
from bot.cogs import channels
import bot.constants as constants

# import discord.py api wrapper
import discord
from discord.ext import commands, tasks

# import python utilities
import sys
from datetime import datetime
import os

# Import the configuration. Whether or not the bot was configured was already tested
from config import bot_token, bot_prefix, bot_description, shutdown_admins, bot_user_id

# Turt bot instance class
class Bot(commands.Bot):
	
	sql = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.connect_to_sqlite()

	def connect_to_sqlite(self):
		# Create connection with database
		self.sql = sql.SQLConnector(constants.db_file)
		if not self.sql.connect():
			sys.exit(-3)

