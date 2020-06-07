#!/usr/bin/env python3

#import discord.py api wrapper
from discord.ext import commands#, cogs
import discord

#import needed utilities
from datetime import datetime

#import config
from config import bot_token, bot_admins, bot_prefix, bot_description

#bot description can be None
bot = commands.Bot(command_prefix=bot_prefix, 
					description=bot_description,
					status=discord.Status.idle,
					activity=discord.Game(name='Starting...'))

usage_prefix = "usage - " + bot_prefix


################ BOT STUFF ############################

@bot.event
async def on_ready():
	print("Bot started at " + datetime.now().strftime("%H:%M:%S"))
	print("bot_prefix: " + bot_prefix)

################ MODERATION COMMANDS ##################

@bot.command()
async def prune(ctx, n=None):
	'''Deletes the previous x number of messages'''
	#usage statement sent when command incorrectly invoked
	usage = "`" + usage_prefix + "prune [number_to_remove]`"
	if n == None: 
		await send(usage)
		return

	n = int(n) #Convert to an integer so it can be used to get channel history up to a limit

	history = await ctx.channel.history(limit=n).flatten()
	#await send("deleting the last " + arg + " messages. This may take a minute.")
	await ctx.channel.delete_messages(history)

bot.run(bot_token)
