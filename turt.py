#!/usr/bin/env python3

#import discord.py api wrapper
from discord.ext import commands
import discord

#import sqlite
import sqlite3

#import needed utilities
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlparse
from sys import exit
import time
import os

#import config
try:
	from config import bot_token, bot_admins, bot_prefix, bot_description, link_only_channels
except:
	print("Turt bot is not configured. In order to run the bot, Turt must be configured in the config.py.template file.")
	exit(-1)

#bot description can be None
bot = commands.Bot(command_prefix=bot_prefix, 
		    description=bot_description,
		    status=discord.Status.idle,
		    activity=discord.Game(name='Starting...'))

usage_prefix = "usage - " + bot_prefix

db_file = "sqlite_database"

cursor = None

################ BOT STUFF ############################

@bot.event
async def on_ready():
	print(f"{bot.user.name}: {bot.user.id}")
	print("Bot started at " + datetime.now().strftime("%H:%M:%S"))
	print("User ids whitelisted:")
	for user_id in bot_admins:
		if user_id != -1:
			print("\t" + str(user_id))
	await bot.change_presence(status=discord.Status.online, activity=discord.Game(name='Moderating'))
	print("Putting all users in database...")
	await setup_database_with_all_users()

@bot.event
async def on_member_join(member):
	determine_if_user_exists(member.id)

@bot.command()
async def ping(ctx):
	await ctx.channel.send("Pong!")
	print(len(ctx.guild.members))
	user_id = ctx.author.id
	determine_if_user_exists(user_id)
	cursor.execute("UPDATE users SET TotalPing = TotalPing + 1 WHERE PersonID = ?", (user_id,))
	conn.commit()

################ MODERATION COMMANDS ##################

class ChannelMod(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		
	@commands.Command
	async def prune(self, ctx, n=None):
		'''Deletes the previous n number of messages'''

		if not is_whitelisted(ctx.author.id): return
	
		#usage statement sent when command incorrectly invoked
		usage = "`" + usage_prefix + "prune [number_to_remove]`"
		if n == None: 
			await send(usage)
			return
	
		# Convert to an integer so it can be used to get channel history up to a limit
		n = int(n)+1 #+1 to compensate for the command message the user sent
	
		history = await ctx.channel.history(limit=n).flatten()
		await ctx.channel.delete_messages(history)
	
   	#Only allow links in certain channels (No extra content allowed)
	@commands.Cog.listener()
	async def on_message(self, msg):
		'''Enforces messaging rules'''
		
		#Determine if the message is posted in a link only channel
		if msg.channel.id in link_only_channels:
			#Determine if the entire message is a link (no other content allowed)
			result = urlparse(msg.content)
			if not all([result.scheme, result.netloc, result.path]):
				await msg.delete()

	@commands.Cog.listener()
	async def on_message_edit(self, before, after):
		'''Enforces editing rules'''
		
		#Determine if the message is posted in a link only channel
		if after.channel.id in link_only_channels:
			#Determine if the entire message is a link (no other content allowed)
			result = urlparse(after.content)
			if not all([result.scheme, result.netloc, result.path]):
				await after.delete() 
				#NOTE: This only works if the message is in the internal message cache
				# If the bot starts up after the message is posted and the bot does not act on it since for any reason,
				# then this will NOT work

class VotingMod(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.Command
	async def callvote(self, ctx, name:str, desc:str, num_days:int):
		'''Creates an election with the given name and description that lasts for the supplied number of days (minimum is 1, decimals allowed, rounds to the nearest hour)'''

		# The user must supply a minimum of 1 day in order to give time for people to vote
		if num_days < 1:
			await send("An election must go for a minimum of 1 day")
			return

		#will later have enforcement functionality
		hours_in_day = 24
		endTime = int(round(time.time()/3600)) + round(hours_in_day*(num_days)) # in hours
		endTimeAsDate = datetime.now() + timedelta(hours=round(hours_in_day*(num_days)))
		cursor.execute("SELECT MAX(ElectionID) FROM elections")
		result = cursor.fetchone()
		if result[0] is None: result = 0 # If there are no elections right now, then we want to do make the id 0
		cursor.execute("INSERT INTO elections VALUES (?, ?, ?, ?, ?, ?, ?)", (result, 0, 0, ctx.guild.id, name, desc, endTime))
		conn.commit()
		await ctx.channel.send("Election created! Vote ends at " + str(endTimeAsDate))

################ UTILITY FUNCTIONS #####################

def is_whitelisted(user_id):
	return user_id in bot_admins

################ DATABASE FUNCTIONS ####################

def determine_if_user_exists(user_id): #And add the user if not
	cursor.execute("SELECT count(*) FROM users WHERE PersonID = ?", (user_id,))
	if cursor.fetchone()[0] == 0:
		cursor.execute("INSERT INTO users VALUES (?, ?)", (user_id, 0))
		conn.commit()
		print("\t\t\tAdded User")

async def setup_database_with_all_users():
	for guild in bot.guilds:
		print("\tchecking in server `" + guild.name + "` (" + str(guild.id) + ")")
		for member in guild.members:
			print("\t\tchecking member `" + str(member) + "` (" + str(member.id) + ")")
			determine_if_user_exists(member.id)

################ STARTUP ###############################

# Determine if the bot has been setup
if not os.path.isfile(db_file):
	print("Turt bot has not been setup. Setup turt bot by running `setup.py`")
	exit(-1)
	
# Create connection with db
conn = None
try:
	conn = sqlite3.connect(db_file)
	cursor = conn.cursor()
except Error as e:
	print(e);
	print("Unable to create a connection with sqlite database `sqlite_database`. It could be corrupted.")
	exit(-2)

# Add all the cogs
bot.add_cog(ChannelMod(bot))
bot.add_cog(VotingMod(bot))

# Run the bot
bot.run(bot_token)
