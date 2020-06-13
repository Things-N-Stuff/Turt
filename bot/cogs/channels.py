#discord.py
import discord
from discord.ext import commands, tasks

class Channels(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.Command
	async def prune(self, ctx, n:int=None):
		'''Whitelist only.
		Deletes the previous n number of messages (Up to 99).'''

		if not await self.bot.get_cog("Permissions").is_whitelisted(ctx.author.id, ctx.guild.id): return

		if n > 99:
			await ctx.channel.send("You can only prune up to 99 messages.")
			return

		# Convert to an integer so it can be used to get channel history up to a limit
		n = int(n)+1 #+1 to compensate for the command message the user sent
	
		history = await ctx.channel.history(limit=n).flatten()
		await ctx.channel.delete_messages(history)

	@commands.Command
	async def setlinkonly(self, ctx, channel_id:int, link_only:str="true"):
		'''Whitelist only.
		Update the link-only status of a channel.
		Turt bot will delete all messages that are not links in link-only channels.
		[link_only] needs to be either 1 (link_only) or 0 (not link_only). Sets to link-only by default if [link_only] not given.'''

		if not await self.bot.get_cog("Permissions").is_whitelisted(ctx.author.id, ctx.guild.id): return

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
	async def on_message(self, msg):
		'''Enforces messaging rules'''
		
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
	async def on_message_edit(self, before, after):
		'''Enforces editing rules'''
		
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
