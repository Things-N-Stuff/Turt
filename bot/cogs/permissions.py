#import discord.py
import discord
from discord.ext import commands, tasks

from bot.decorators import server_only, server_owner_only


class Permissions(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    # Allow only server owners to whitelist users for ONLY their server (for using commands like `prune` and `electionchannel`)
    @commands.Command
    @server_only()
    @server_owner_only()
    async def whitelist(self, ctx, userid:int, whitelisted:str):
        '''
        Permissions Requirement: Server Owner
        Parameters:
            userid - The discord userid of the user to have their whitelist status updated.
                Must be 'true' or 'false'.
        Description:
            Whitelist a specific user for this server, which allows them to use whitelist-only commands.
        '''
        whitelisted = whitelisted.lower() #Make is case insensitive
        
        self.bot.sql.cursor.execute("SELECT userid FROM whitelist WHERE serverid=?", (ctx.guild.id,))
        whitelisted_users = self.bot.sql.cursor.fetchall()
        
        #If attempting to remove whitelist on the user
        if whitelisted == "false":
            if (userid,) in whitelisted_users:
                self.bot.sql.cursor.execute("DELETE FROM whitelist WHERE userid=? AND serverid=?", (userid, ctx.guild.id,))
                self.bot.sql.conn.commit()
                await ctx.channel.send("User successfully unwhitelisted")
            else:
                await ctx.channel.send("That user is not whitelisted on this server.")
                return
        
        #If attempting to whitelist the user
        elif whitelisted == "true":
            if(userid,) not in whitelisted_users:
                self.bot.sql.cursor.execute("INSERT INTO whitelist VALUES(?,?)", (ctx.guild.id, userid))
                self.bot.sql.conn.commit()
                await ctx.channel.send("User successfully whitelisted")
                #Now allow them to make elections without a timeout
                self.bot.sql.cursor.execute("UPDATE users SET WhenCanVoteNext=0 WHERE userid=?", (userid,))
                self.bot.sql.conn.commit()
            else:
                await ctx.channel.send("That user is already whitelisted on this server.")
                return
        else:
            await ctx.channel.send("[whitelisted] must either be 'true' or 'false'.")

    def is_whitelisted(self, user_id, server_id) -> bool:
        self.bot.sql.cursor.execute("SELECT userid FROM whitelist WHERE serverid=? AND userid=?", (server_id, user_id))
        user = self.bot.sql.cursor.fetchone() #If this is None, then the user is not whitelisted
        server = self.bot.get_guild(server_id)
        if server is None: return False
        return user is not None or server.owner_id == user_id #The server owner is not in the whitelisted table, but is always whitelisted
        
def setup(bot: commands.Bot) -> None:
    bot.add_cog(Permissions(bot))
