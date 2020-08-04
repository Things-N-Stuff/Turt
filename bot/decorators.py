# discord
import discord
from discord.ext import commands

# python
from typing import Callable

# checks
from bot.checks import in_server, is_whitelisted, is_server_owner, is_bot_hoster

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

def bot_hoster_only() -> Callable:
    def predicate(ctx:commands.Context):
        return is_bot_hoster(ctx)

    return commands.check(predicate)
