#discord.py
import discord
from discord.ext import commands, tasks

from urllib.parse import urlparse

from bot.decorators import server_only
from bot.decorators import whitelist_only

class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Command
    @server_only()
    @whitelist_only()
    async def prune(self, ctx, n:int=None):
        '''
        Permissions Requirement: Server Whitelisted
        Parameter Notes:
            n - The number of messages to delete. Maximum of 99.
        Description:
            Deletes the previous n number of messages (up to 99) [1].
        Notes:
            [1] Turt bot must have the `manage messages` permission for it to delete messages.
        '''

        if n > 99:
            await ctx.channel.send("You can only prune up to 99 messages.")
            return

        # Convert to an integer so it can be used to get channel history up to a limit
        n = int(n)+1 #+1 to compensate for the command message the user sent
        
        history = await ctx.channel.history(limit=n).flatten()
        await ctx.channel.delete_messages(history)

    @commands.Command
    @server_only()
    @whitelist_only()
    async def setlinkonly(self, ctx, channel_id:int, link_only:str="true"):
        '''
        Permissions Requirement: Server Whitelisted
        Parameter Notes:
            channel_id - The id of the channel to be modified.
            link_only - The new `link_only` status of a channel. Should be `true` or `false`.
                If not provided, then defaults to `true`.
        Description:
            Update the link-only status of a channel.
            Turt bot will delete all messages that are not links in link-only channels [1].
        Notes:
            [1] Turt bot must have the `manage messages` permission for it to delete messages.
            [2] Messages in link-only channels must start with links but can have following messages.
        '''

        link_only = link_only.lower()

        #Determine if valid action is used (link_only is True or False)
        if link_only != "true" and link_only != "false":
            await ctx.channel.send("[link_only] must either be 'true' or 'false'.")
            return

        #Determine if the channel id is in this server
        channel = await self.bot.fetch_channel(channel_id)
        if channel is None or channel.guild.id != ctx.guild.id:
            await ctx.channel.send("That channel does not exist in this server. Unable to change its link-only status.")
            return

        #Get all link only channels for this server
        self.bot.sql.cursor.execute("SELECT channelid FROM linkonlychannels WHERE serverid=?", (ctx.guild.id,))
        channels = self.bot.sql.cursor.fetchall()

        #If making link only, make sure the channel is not already flagged as link only
        if link_only == "true":
            if (channel_id,) in channels:
                await ctx.channel.send("That channel is already flagged as link-only.")
                return
            else:
                self.bot.sql.cursor.execute("INSERT INTO linkonlychannels VALUES (?,?)", (channel_id, ctx.guild.id))
                await ctx.channel.send("Set #" + channel.name + " to link-only.")

        #If making not link only, make sure the channel is not already flagged as not link only
        if link_only == "false":
            if (channel_id,) not in channels:
                await ctx.channel.send("That channel is not flagged as link-only.")
                return
            else:
                self.bot.sql.cursor.execute("DELETE FROM linkonlychannels WHERE channelid=?", (channel_id,))
                await ctx.channel.send("Set #" + channel.name + " to not link-only.")

        self.bot.sql.conn.commit()

    #Only allow links in certain channels (No extra content allowed)
    @commands.Cog.listener()
    @server_only()
    async def on_message(self, msg):
        '''Enforces messaging rules'''
        if msg.guild is None: return # This is in a dm
                
        #Get the all link only channels in this server
        self.bot.sql.cursor.execute("SELECT channelid FROM linkonlychannels WHERE serverid=?", (msg.guild.id,))
        link_only_channels = self.bot.sql.cursor.fetchall()
        #Determine if the message is posted in a link only channel
        if (msg.channel.id,) in link_only_channels:
            #Determine if the entire message is a link (no other content allowed, except for trailing)
            result = urlparse(msg.content)
            if not all([result.scheme, result.netloc, result.path]):
                await msg.delete()

    @commands.Cog.listener()
    @server_only()
    async def on_message_edit(self, before, after):
        '''Enforces editing rules'''
        if after.guild is None: return # This is in a dm
                
        #Get the all link only channels in this server
        self.bot.sql.cursor.execute("SELECT channelid FROM linkonlychannels WHERE serverid=?", (after.guild.id,))
        link_only_channels = self.bot.sql.cursor.fetchall()
        #Determine if the message is posted in a link only channel
        if (after.channel.id,) in link_only_channels:
            #Determine if the entire message is a link (no other content allowed, except for trailing)
            result = urlparse(after.content)
            if not all([result.scheme, result.netloc, result.path]):
                await after.delete()
                #NOTE: This only works if the message is in the internal message cache
                # If the bot starts up after the message is posted and the bot does not act on it since for any reason,
                # then this will NOT work


def setup(bot: commands.Bot) -> None:
    '''Load the channels cog'''
    bot.add_cog(Channels(bot))
