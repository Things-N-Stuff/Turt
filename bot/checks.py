import discord
from discord.ext import commands

from bot import constants

from bot.errors import NotInServer
from bot.errors import NotWhitelisted

def in_server(ctx:commands.Context) -> bool:
	return ctx.guild is not None

def is_whitelisted(ctx:commands.Context) -> bool:
	return constants.bot.get_cog("Permissions").is_whitelisted(ctx.author.id, ctx.guild.id)
