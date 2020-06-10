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
	from config import bot_token, bot_admins, bot_prefix, bot_description, link_only_channels, shutdown_admins
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
	print("Discord.py " + discord.__version__)
	print(f"{bot.user.name}: {bot.user.id}")
	print("Bot started at " + datetime.now().strftime("%H:%M:%S"))
	print("User ids whitelisted:")
	for user_id in bot_admins:
		if user_id != -1:
			print("\t" + str(user_id))
	await bot.change_presence(status=discord.Status.online, activity=discord.Game(name='Moderating'))
	print("Putting all users in database...")
	await setup_database_with_all_users()

#Input error handling
@bot.event
async def on_command_error(ctx, error):
	print(error)
	await ctx.send_help(ctx.command)

@bot.event
async def on_member_join(member):
	determine_if_user_exists(member.id)

# Allow only specially whitelisted people to shut the bot down
@bot.command
async def shutdown(ctx):
	'''Shutdown the bot in case of an emergency and bot hoster does not have direct access to the bot'''	

	if not ctx.author.id in shutdown_admins: return

	await ctx.channel.send("Shutting down...")
	conn.commit() # Ensure that everything was saved
	exit(1)

################ MODERATION COMMANDS ##################

class Channels(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.Command
	async def prune(self, ctx, n:int=None):
		'''Deletes the previous n number of messages (Up to 99)'''

		if not is_whitelisted(ctx.author.id): return

		if n > 99:
			await ctx.channel.send("You can only prune up to 99 messages.")
			return

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
	async def callvote(self, ctx, name:str, desc:str, num_days:int, thumbnail:str=None):
		'''Creates an election with the given name and description that lasts for the supplied number of days (minimum is 1, decimals allowed, rounds to the nearest hour)'''

		# The election channel must be configured in order to create elections
		cursor.execute("SELECT * FROM servers WHERE ServerID=?", (ctx.guild.id,))
		first = cursor.fetchone()
		voting_channel_id = None
		if first is None: determine_if_server_exists(ctx.guild.id,) # Add the server to the database if the server does not exist
		else: voting_channel_id = first[1]
		if voting_channel_id is None or voting_channel_id == -1: # Not configured
			await ctx.channel.send("The election channel has not been configured for this server.\n`./t electionchannel [channelID]` to setup election channel.")
			return

		# Make sure the user has not voted in the last 12 hours in any election
		next_time_index = 1 # The index of when the user can create an election next
		current_time_in_hours = int(round(time.time()/3600))
		cursor.execute("SELECT * FROM users WHERE UserID=?", (ctx.author.id,))# b/c nobody has that userid
		first = cursor.fetchone()
		next_time = 0
		if first is None: determine_if_user_exists(ctx.author.id,) #Add the user to the database if they are not there
		else: next_time = first[next_time_index]
		if next_time is not None and next_time is not "" and next_time is not 0 and next_time > current_time_in_hours: #The person has voted in the last 6 hours
			await ctx.channel.send("You can only create an election every 12 hours. You will be able to create an election in " + str(next_time - current_time_in_hours) + " hours.")
			return

		# The user must supply a minimum of 1 day in order to give time for people to vote
		if num_days < 1:
			await ctx.channel.send("An election must go for a minimum of 1 day")
			return

		#Getting time
		hours_in_day = 24
		additional_hours = round(hours_in_day*(num_days))
		endTime = int(round(time.time()/3600)) + additional_hours # in hours
		endTimeAsDate = datetime.now().replace(microsecond=0, second=0, minute=0) + timedelta(hours=additional_hours) + timedelta(hours=1) #Hours should round up

		
		cursor.execute("SELECT MAX(ElectionID) FROM elections") # We want to new id to be the next id not used
		electionID = cursor.fetchone()[0]
		if electionID is None: electionID = -1 # If there are no elections right now, then we want to do make the id 0 (Note: adds 1)

		# Send election message in election channel
		election_embed = discord.Embed()
		election_embed.set_author(name="Initiated by " + ctx.author.display_name, icon_url=ctx.author.avatar_url)
		if thumbnail is not None: election_embed.set_thumbnail(url=thumbnail)
		election_embed.title = "New Election: " + name.title()
		election_embed.description = desc.capitalize()
		election_embed.set_footer(text="Vote by reacting with :thumbsup: or :thumbsdown:")
		
		#Time left field
		#current_time_in_hours = int(round(time.time()/3600))
		election_embed.add_field(name="Time Left", value=str(additional_hours) + " Hours", inline=True)

		election_embed.add_field(name="ID", value="`"+str(electionID+1)+"`", inline=True) #We want this as code block to make it look good
		message = await bot.get_channel(voting_channel_id).send(embed=election_embed) #Send it to the voting channel

		cursor.execute("INSERT INTO elections VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (electionID+1, message.id, ctx.guild.id, ctx.author.id, name, desc, endTime, thumbnail))
		cursor.execute("UPDATE users SET WhenCanVoteNext = ? WHERE UserID = ?", (current_time_in_hours+12, ctx.author.id))
		conn.commit()

		await ctx.channel.send("Election created! Vote ends at " + str(endTimeAsDate))

	@commands.Command
	async def electionchannel(self, ctx, channelid:int):
		'''Set the channel in which election messages will be sent'''

		if not is_whitelisted(ctx.author.id): return

		if ctx.guild.get_channel(channelid) is not None: #Set the election channel (Must exist on this server)
			cursor.execute("UPDATE servers SET ElectionChannelID = ? WHERE ServerID = ?", (channelid, ctx.guild.id))
			conn.commit()
			await ctx.channel.send("Election message channel successfully updated to '" + ctx.guild.get_channel(channelid).name + "'")
		else:
			await ctx.channel.send("Channel with id '" + str(channelid) + "' does not exist on this server.")


	@tasks.loop(seconds=59) 
	async def check_votes(self):
		await self.bot.wait_until_ready()
		has_checked_votes = False
		if datetime.now().minute == 0 or not has_checked_votes: #Now check all
			cursor.execute("SELECT * FROM elections")
			current_time_in_hours = int(round(time.time()/3600))
			election_id_index = 0
			message_id_index = 1
			server_index = 2
			initiating_user_index = 3
			name_index = 4
			desc_index = 5
			end_time_index = 6
			thumbnail_index = 7
			for row in cursor.fetchall():
				server_id = row[server_index]

				vote_channel_id = None
				cursor.execute("SELECT * FROM servers WHERE ServerID=?", (server_id,))
				result = cursor.fetchone()
				if result is None: # The server isnt stored in the database, so add it
					determine_if_server_exists()
					return
				else: vote_channel_id = result[1]

				if vote_channel_id == -1: return # The server election channel has not been setup yet

				#Update time
				channel = bot.get_channel(int(vote_channel_id))
				election_message = await channel.fetch_message(row[message_id_index])

				current_time_in_hours = int(round(time.time()/3600))
				time_left = row[end_time_index] - current_time_in_hours

				message = ""
				if time_left < 1:
					message = "< 1 Hour"
				else:
					message = str(time_left) + " Hours"

				embed = election_message.embeds[0]
				embed.set_field_at(index=0, name="Time Left", value=message, inline=True)
				await election_message.edit(embed=embed)

				#If the vote is over:
				if current_time_in_hours > row[end_time_index]: #Vote has concluded
					# Send message to channel

					if vote_channel_id == -1: return

					yes=0
					no=0

					channel = bot.get_channel(int(vote_channel_id))
					message = await channel.fetch_message(row[message_id_index])

					for reaction in message.reactions:
						if reaction.emoji == "👍":
							yes = reaction.count
						if reaction.emoji == "👎":
							no = reaction.count

					message=""

					if(yes > no): # Note that it has to be a simple majority (tie does not count)
						message = "The majority voted :thumbsup:!"
					elif(yes < no):
						message = "The majority says :thumbsdown:!"
					else:
						message = "The vote was a tie! (Simple majority not acquired)"

					#To say who initiated the vote, we need to get the member
					user_id = row[initiating_user_index]
					server = await bot.fetch_guild(server_id)
					user = await server.fetch_member(user_id)

					#Vote conclusion embed message
					vote_embed = discord.Embed()
					vote_embed.title = "Election Concluded: " + row[name_index].title()
					vote_embed.description = message
					if row[thumbnail_index] is not None: vote_embed.set_thumbnail(url=row[thumbnail_index])
					vote_embed.set_author(name="Initiated by " + user.display_name, icon_url=user.avatar_url)
					vote_embed.add_field(name="Description", value=row[desc_index].capitalize(), inline=False)
					vote_embed.add_field(name="Yes", value=yes, inline=True)
					vote_embed.add_field(name="No", value=no, inline=True)
					vote_embed.set_footer(text="ID: " + str(row[election_id_index]))

					channel = bot.get_channel(int(vote_channel_id))
					await channel.send(embed=vote_embed)

					# Remove election from database
					cursor.execute("DELETE FROM elections WHERE ElectionID=?", (row[election_id_index],))
					conn.commit()

					# Fix original message
					channel = bot.get_channel(int(vote_channel_id))
					message = await channel.fetch_message(row[message_id_index])

					embed = message.embeds[0]
					embed.set_field_at(index=0, name="Time Left", value="Election Ended", inline=True)
					await message.edit(embed=embed)
					
					# TODO:Enforce the vote (implement later)
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
	cursor.execute("SELECT count(*) FROM users WHERE UserID = ?", (user_id,))
	if cursor.fetchone()[0] == 0:
		cursor.execute("INSERT INTO users VALUES (?, ?)", (user_id, ""))
		conn.commit()
		print("\t\t\tAdded member (" + str(user_id) + ")")

async def setup_database_with_all_users():
	for guild in bot.guilds:
		print("\tchecking in server `" + guild.name + "` (" + str(guild.id) + ")")
		determine_if_server_exists(guild.id)
		for member in guild.members:
			determine_if_user_exists(member.id)

################ STARTUP ###############################

# Determine if the bot has been setup
if not os.path.isfile(db_file):
	print("Turt bot has not been setup. Setup turt bot by running `python3 setup.py`")
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
