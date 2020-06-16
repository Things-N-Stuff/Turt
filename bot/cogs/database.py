#import discord.py
import discord
from discord.ext import commands, tasks


class Database(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        bot.sql.determine_if_user_exists(member.id)

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Database(bot))
