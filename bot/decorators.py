# discord
import discord
from discord.ext import commands

# python
from typing import Callable

# checks
from bot.checks import in_server
from bot.checks import is_whitelisted
from bot.checks import is_server_owner

# We currently have none

def server_only() -> Callable:
	def predicate(ctx:commands.Context):
		return in_server(ctx)

	return commands.check(predicate)

def whitelist_only() -> Callable:
	def predicate(ctx:commands.Context):
		return is_whitelisted(ctx) #Needs to be awaited

	return commands.check(predicate)

def server_owner_only() -> Callable:
	def predicate(ctx:commands.Context):
		return is_server_owner(ctx)
	
	return commands.check(predicate)
