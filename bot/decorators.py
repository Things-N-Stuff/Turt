# discord
import discord
from discord.ext import commands

# python
from typing import Callable

# checks
from bot.checks import in_server

# We currently have none

def server_only() -> Callable:
	def predicate(ctx:commands.Context):
		return in_server(ctx)

	return commands.check(predicate)
