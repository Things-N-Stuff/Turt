#discord.py
import discord
from discord.ext import commands, tasks

#Python utilites
import sys
import os

#Import needed config
from config import shutdown_admins

from bot.decorators import bot_hoster_only

class BotHosting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Allow only specially whitelisted people to shut the bot down (in bot_shutdown)
    @commands.command()
    @bot_hoster_only()
    async def shutdown(self, ctx):
        '''
        Permissions Requirement: Bot Hoster Whitelisted
        Description:
            Kill the bot process.
        '''
        await self.bot.wait_until_ready()
        
        if not ctx.author.id in shutdown_admins: return
        
        await ctx.channel.send("Shutting down...")
        try:
            self.bot.sql.conn.commit()
            self.bot.sql.disconnect()
            await self.bot.close()
        except:
            sys.exit(1) 

    @commands.command()
    @bot_hoster_only()
    async def restart(self, ctx):
        '''
        Permissions Requirement: Bot Hoster Whitelisted
        Description:
            Create a new bot process and kill this one[1].
            Useful for applying updates.
        Notes:
            [1] The system the bot is hosted on must have the *default* python version be >= python 3.6
        '''
        await self.bot.wait_until_ready()
        
        if not ctx.author.id in shutdown_admins: return
        
        await ctx.channel.send("Restarting...")
        try:
            self.bot.sql.conn.commit()
            self.bot.sql.disconnect()
            # spawn process
            os.system("python3 turt.py")
            await self.bot.close()
        except:
            # spawn process
            os.system("python3 turt.py")
            sys.exit(2)


def setup(bot: commands.Bot) -> None:
    '''Load the bothosting cog'''
    bot.add_cog(BotHosting(bot))
