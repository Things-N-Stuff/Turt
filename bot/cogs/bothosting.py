#discord.py
import discord
from discord.ext import commands, tasks

#Python utilites
import sys

#Import needed config
from config import shutdown_admins

class BotHosting(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	# Allow only specially whitelisted people to shut the bot down (in bot_shutdown)
	@commands.Command
	async def shutdown(ctx):
		'''Shutdown the bot in case of an emergency and bot hoster does not have direct access to the bot.
		In order to shutdown the bot, you must be given permission by the bot hoster.'''	
	
		if not ctx.author.id in shutdown_admins: return
	
		await ctx.channel.send("Shutting down...")
		conn.commit() # Ensure that everything was saved
		try:
			await bot.close()
		except:
			sys.exit(1)	

	@commands.Command
	async def restart(ctx):
		'''Restart the process. Must be whitelisted to restart the bot.
		In order to restart the bot, you must be given permission by the bot hoster.'''
	
		if not ctx.author.id in shutdown_admins: return
	
		await ctx.channel.send("Restarting...")
		try:
			# spawn process
			os.system("python3.6 turt.py")
			await bot.close()
		except:
			# spawn process
			os.system("python3.6 turt.py")
			sys.exit(2)


def setup(bot: commands.Bot) -> None:
	'''Load the bothosting cog'''
	bot.add_cog(BotHosting(bot))
