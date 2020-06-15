import discord
from discord.ext import commands

from bot import constants

from bot.errors import NotInServer
from bot.errors import NotWhitelisted

from config import shutdown_admins

def in_server(ctx:commands.Context) -> bool:
	return ctx.guild is not None

def is_whitelisted(ctx:commands.Context) -> bool:
	return constants.bot.get_cog("Permissions").is_whitelisted(ctx.author.id, ctx.guild.id)

def is_server_owner(ctx:commands.Context) -> bool:
	return ctx.author.id == ctx.guild.id

def is_bot_hoster(ctx:commands.Context) -> bool:
	return ctx.author.id in shutdown_admins
