import discord
from discord.ext import commands

def in_server(ctx:commands.Context) -> bool:
	return ctx.guild is not None

#def is_whitelisted(ctx:commands.Context) -> bool:
#	return 
