#!/usr/bin/env python3.6

#import discord.py api wrapper
from discord.ext import commands, tasks
import discord

#import sqlite
import sqlite3
from sqlite3 import Error

#import needed utilities
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlparse
from sys import exit
import time
from time import sleep
import os
from threading import Thread
import asyncio

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
	print(discord.__version__)
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

################ MODERATION COMMANDS ##################

class Channels(commands.Cog):
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

class Voting(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.check_votes.start()

	@commands.Command
	async def vote(self, ctx, electionID:int , vote:str):
		'''Casts your ballot for a specific election'''

		# TODO:Ensure that the user has not voted yet

		# Ensure that the election is in the server the command is sent in
		cursor.execute("SELECT * FROM elections WHERE ElectionID=?", (electionID,))
		result = cursor.fetchone()
		if ctx.guild.id != result[3]: # We also need to make sure that the election is in this server
			await ctx.channel.send("We are unaware of an election with ID '" + str(electionID) + "'. `./t elections` to see current elections for this server.")
			await ctx.channel.send("If you are voting in an election for a different server, you must vote in that server.")
			return

		# Ensure that the user is casting a valid choice ("yes" or "no")
		if vote.lower() != "yes" and vote.lower() != "no":
			await ctx.channel.send("Invalid ballot. You must either choose 'yes' or 'no'.")
			return

		# Update the database because good ballot and in correct server
		if vote.lower() == "yes":
			cursor.execute("UPDATE elections SET yes=yes+1 WHERE ElectionID=?", (electionID,))
		elif vote.lower() == "no":
			cursor.execute("UPDATE elections SET no=no+1 WHERE ElectionID=?", (electionID,))
		conn.commit()

		# Tell the user their ballot has been accepted
		await ctx.channel.send("Your ballot ('" + vote + "') has been accepted for election '" + result[4] + "' (`" + str(electionID) + "`)")

	@commands.Command
	async def elections(self, ctx):
		'''See information on elections in your server'''

		cursor.execute("SELECT * FROM elections WHERE ServerID=?", (ctx.guild.id,))

		all_elections = cursor.fetchall() 
		if len(all_elections) == 0: #There are no current elections in the server
			await ctx.channel.send("There are no ongoing elections in " + ctx.guild.name + ". `./t callvote [name] [desc] [ndays]` to make one!")
			return

		#Begin creating the embed that tells the user the current elections
		elections_embed = discord.Embed()
		elections_embed.title = "Ongoing Elections in " + ctx.guild.name
		elections_embed.description = "`./t electioninfo [ID]` for more info on an election.\nVote with `./t vote [electionID] [yes/no]`"
		for election in all_elections: #Add each election on its own line
			elections_embed.add_field(name="Name", value=election[4].title(), inline=True)
			elections_embed.add_field(name="ID", value="`"+str(election[0])+"`", inline=True) #We want this as code block to make it look good

			#Time left field
			current_time_in_hours = int(round(time.time()/3600))
			time_left = election[6] - current_time_in_hours
			message = str(time_left) + " Hours"
			if time_left < 1: message = "< 1 Hour"
			elections_embed.add_field(name="Time Left", value=message, inline=True)
		await ctx.channel.send(embed=elections_embed) #send it

	@commands.Command
	async def electioninfo(self, ctx, electionID):
		'''See more detailed information on an election'''

		cursor.execute("SELECT * FROM elections WHERE ElectionID=?", (electionID,))
		election = cursor.fetchone()
		if ctx.guild.id != election[3]: # We also need to make sure that the election is in this server
			await ctx.channel.send("We are unaware of an election with id '" + str(electionID) + "'. `./t elections` to see current elections for this server.")
			return

		#Begin creating the embed that tells the user the current elections
		elections_embed = discord.Embed()
		elections_embed.title = election[4].title() + " - Ongoing Election"
		elections_embed.description = election[5].capitalize()
		elections_embed.add_field(name="ID", value="`"+str(election[0])+"`", inline=True) #We want this as code block to make it look good

		#Time left field
		current_time_in_hours = int(round(time.time()/3600))
		time_left = election[6] - current_time_in_hours
		message = str(time_left) + " Hours"
		if time_left < 1: message = "< 1 Hour"
		elections_embed.add_field(name="Time Left", value=message, inline=True)
		await ctx.channel.send(embed=elections_embed) #send it

	@commands.Command
	async def callvote(self, ctx, name:str, desc:str, num_days:int):
		'''Creates an election with the given name and description that lasts for the supplied number of days (minimum is 1, decimals allowed, rounds to the nearest hour)'''

		# The user must supply a minimum of 1 day in order to give time for people to vote
		if num_days < 1:
			await send("An election must go for a minimum of 1 day")
			return

		#Getting time
		hours_in_day = 24
		additional_hours = round(hours_in_day*(num_days))
		endTime = int(round(time.time()/3600)) + additional_hours # in hours
		endTimeAsDate = datetime.now().replace(microsecond=0, second=0, minute=0) + timedelta(hours=additional_hours) + timedelta(hours=1) #Hours should round up

		
		cursor.execute("SELECT MAX(ElectionID) FROM elections") # We want to new id to be the next id not used
		result = cursor.fetchone()[0]
		if result is None: result = -1 # If there are no elections right now, then we want to do make the id 0 (Note: adds 1)
		cursor.execute("INSERT INTO elections VALUES (?, ?, ?, ?, ?, ?, ?)", (result+1, 0, 0, ctx.guild.id, name, desc, endTime))
		conn.commit()
		await ctx.channel.send("Election created! Vote ends at " + str(endTimeAsDate))

	@commands.Command
	async def votingchannel(self, ctx, channelid:int):
		'''Set the channel in which election/voting messages will be sent'''

		if not is_whitelisted(ctx.author.id): return

		if ctx.guild.get_channel(channelid) is not None: #Set the election channel (Must exist on this server)
			cursor.execute("UPDATE servers SET ElectionChannelID = ? WHERE ServerID = ?", (channelid, ctx.guild.id))
			conn.commit()
			await ctx.channel.send("Election message channel successfully updated to '" + ctx.guild.get_channel(channelid).name + "'")
		else:
			await ctx.channel.send("Channel with id '" + channelid + "' does not exist on this server.")


	@tasks.loop(seconds=59) 
	async def check_votes(self):
		await self.bot.wait_until_ready()
		has_checked_votes = False
		if datetime.now().minute == 0 or not has_checked_votes: #Now check all
			cursor.execute("SELECT * FROM elections")
			current_time_in_hours = int(round(time.time()/3600))
			end_time_index = 6
			server_index = 3
			election_id_index = 0
			for row in cursor.fetchall():
				if current_time_in_hours > row[end_time_index]: #Vote has concluded
					server_id = row[server_index]
					# Send message to channel
					cursor.execute("SELECT * FROM servers WHERE ServerID=?", (server_id,))
					vote_channel_id = cursor.fetchone()[1]

					yes=row[1]
					no=row[2]

					message=""

					if(yes > no): # Note that it has to be a simple majority (tie does not count)
						message = "The majority says \"Yes\"!"
					if(yes < no):
						message = "The majority says \"No\"!"
					else:
						message = "The vote was a tie!"

					#Vote conclusion embed message
					vote_embed = discord.Embed()
					vote_embed.title = row[4].capitalize() + " - Vote has concluded!"
					vote_embed.description = message
					vote_embed.add_field(name="Description", value=row[5].capitalize(), inline=False)
					vote_embed.add_field(name="Yes", value=yes, inline=True)
					vote_embed.add_field(name="No", value=no, inline=True)

					#Send message - Idk why I have to do it this way, but doing `bot.get_channel(id)` stalls the entire thing
					server = await bot.fetch_guild(server_id)
					for channel in await server.fetch_channels():
						if channel.id == vote_channel_id:
							await channel.send(embed=vote_embed)

					#channel = bot.get_channel(int(vote_channel_id))
					#await channel.send("Vote has concluded!")

					# Remove election from database
					cursor.execute("DELETE FROM elections WHERE ElectionID=?", (row[election_id_index],))
					conn.commit()
	
					# Enforce the vote (implement later)
			has_checked_votes = True

################ UTILITY FUNCTIONS #####################

def is_whitelisted(user_id):
	return user_id in bot_admins

################ DATABASE FUNCTIONS ####################

def determine_if_server_exists(server_id): #And add the server if not
	cursor.execute("SELECT count(*) FROM servers WHERE ServerID = ?", (server_id,))
	if cursor.fetchone()[0] == 0:
		cursor.execute("INSERT INTO servers VALUES (?, ?)", (server_id, -1))
		conn.commit()
		print("\t\tAdded Server")

def determine_if_user_exists(user_id): #And add the user if not
	cursor.execute("SELECT count(*) FROM users WHERE PersonID = ?", (user_id,))
	if cursor.fetchone()[0] == 0:
		cursor.execute("INSERT INTO users VALUES (?)", (user_id,))
		conn.commit()
		print("\t\t\tAdded member (" + str(user_id) + ")")

async def setup_database_with_all_users():
	for guild in bot.guilds:
		print("\tchecking in server `" + guild.name + "` (" + str(guild.id) + ")")
		determine_if_server_exists(guild.id)
		for member in guild.members:
			#print("\t\tchecking member `" + str(member) + "` (" + str(member.id) + ")")
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
bot.add_cog(Channels(bot))
bot.add_cog(Voting(bot))

# Run the bot
bot.run(bot_token)
