#!/usr/bin/env python3

#import discord.py api wrapper
from discord.ext import commands#, cogs
import discord

#import needed utilities
from datetime import datetime
from urllib.parse import urlparse

#import config
from config import bot_token, bot_admins, bot_prefix, bot_description, link_only_channels

#bot description can be None
bot = commands.Bot(command_prefix=bot_prefix, 
		    description=bot_description,
		    status=discord.Status.idle,
		    activity=discord.Game(name='Starting...'))

usage_prefix = "usage - " + bot_prefix


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

################ MODERATION COMMANDS ##################

class ChannelMod(commands.Cog):
	def init(self, bot):
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

################ UTILITY FUNCTIONS #####################

def is_whitelisted(user_id):
	return user_id in bot_admins

# Add all the cogs
bot.add_cog(ChannelMod(bot))

# Run the bot
bot.run(bot_token)
