#import discord.py
import discord
from discord.ext import commands, tasks

#python utility libraries
from datetime import datetime, timedelta
import time
import traceback

#checks
from bot.decorators import server_only
from bot.decorators import whitelist_only

#config
import config
import math

class Discipline(commands.Cog):

    has_not_checked_bans = True

    def __init__(self, bot):
        self.bot = bot
        self.check_bans.start()

    @commands.Command
    @server_only()
    @whitelist_only()
    async def warn(self, ctx, user:discord.User, severity:int, reason:str):
        '''
        Permissions Requirement: 
            Warning Whitelisted Users: Server Owner
            Warning Non-Whitelisted Users: Server Whitelisted
        Parameters:
            user - An @ mention or the userid of the user to be warned.
            severity - How severe the offense was. This number is added to the user's account for this server.
            reason - The reason for warning the user. It is recommended to issue warnings to whitelisted users who warn without adequate reason, or even for whitelist status to be revoked in extreme cases.
        Description:
            Warn a user for something they did and add <severity> severity points to their account for this server.
            Once a punishable number of severity points has been reached, then a punishment is automatically issued [2][3].
                If multiple punishable severity levels are surpassed, then the longest ban is issued.
            Punishments: [1]
                10 severity points - banned for 1 hour
                20 severity points - banned for 1 day
                30 severity points - banned for 1 week
                Every 10 severity points afterwards will result in a 1 month ban (30 days)
            When banning users, Turt bot will send a DM including a server invite [4].
            After the ban has expired, Turt bot will unban the user [3].

        Notes:
            [1] Ban punishments round up to the next hour.
            [2] Turt bot cannot ban users with roles higher in the role hierarchy. If a user should be banned, consult someone who is higher in the hierarchy.
            [3] It is recommended to turn on the `ban members` permission for Turt, or Turt will be unable to ban or automatically unban users when their ban has expired.
            [4] It is recommended to turn on the `manage server` permission for Turt, or Turt will be unable to send server invites to banned users.
        '''

        bans_in_hours = [1, 24, 168, 720] #Note that month bans are 30 days (they dont vary with month)
        bans_strings = ["1 hour", "1 day", "1 week", "30 days"]

        cursor = self.bot.sql.cursor
        conn = self.bot.sql.conn

        user_id = user.id

        #Users cannot warn themselves
        if user_id == ctx.author.id:
            await ctx.channel.send("You cannot warn yourself.")
            return
                        
        #Determine if the person giving the warning is the server owner (they can warn anyone)
        if user_id != ctx.guild.owner_id: # whitelisted people cannot warn other whitelisted people     
            #Determine if the person being warned is whitelisted
            cursor.execute("SELECT * FROM whitelist WHERE serverid=? AND userid=?", (ctx.guild.id, user_id))
            result = cursor.fetchone()
            if result is not None: #Then the person is whitelisted
                await ctx.channel.send("Only the server owner can warn whitelisted users.")
                return
                #If the person giving the warning is not the server owner, then do nothing

        # Determine whether or not the user exists in this server
        if user is None:
            await ctx.channel.send("That user does not exist on this server")
            return

        if user.id == config.bot_user_id:
            await ctx.channel.send("You cannot warn me.")
            return

        if user.bot:
            await ctx.channel.send("You cannot warn bots.")
            return

        if severity < 0:
            await ctx.channel.send("You cannot give users negative severity points.")
            return

        if len(reason.strip()) == 0:
            await ctx.channel.send("Warn reason cannot be whitespace.")
            return

        # Determine the number of severity points they now have
        cursor.execute("SELECT severitypoints FROM warnings WHERE userid=? AND serverid=?", (user_id, ctx.guild.id))
        severity_points = cursor.fetchone()
        if severity_points is None: #This person has not been warned before so add them
            cursor.execute("INSERT INTO warnings VALUES (?,?,?,?)", (user_id, ctx.guild.id, 0, -1))
            conn.commit()
            severity_points = 0
        else:
            severity_points = severity_points[0]

        total_severity_points = severity_points + severity

        cursor.execute("UPDATE warnings SET severitypoints=? WHERE userid=? AND serverid=?", (total_severity_points, user_id, ctx.guild.id))
        conn.commit()

        # Determine their punishment (if they have reached a punishment)

        punished = False
        current_time_in_hours = int(math.ceil(time.time()/3600)) # Rounded up
        end_hour = current_time_in_hours
        ban_level = 0
        if math.ceil(severity_points/10) <= math.floor(total_severity_points/10) and severity_points % 10 != 0: #There will be a punishment
            index = math.floor(total_severity_points/10)-1
            if index > 3: index = 3 #The max punishment has an index of 3
            punished = True
            end_hour += bans_in_hours[index]
            ban_level = index

        if severity == 0: 
            punished = False

        if punished:

            server = await self.bot.fetch_guild(ctx.guild.id)
            bot_user = await server.fetch_member(config.bot_user_id)
            member = await server.fetch_member(user_id)
            if bot_user.guild_permissions.ban_members and bot_user.top_role.position > member.top_role.position:
        
                # Notify via dm and in the channel (Use different point of view for each)
                ban_embed = discord.Embed()
                ban_embed.color = discord.Colour.red()
                ban_embed.set_author(name=f"Last warned by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
                ban_embed.title = f"You have been banned from {ctx.guild.name} for {bans_strings[ban_level]}."
                ban_embed.description = f"The last straw:\n{reason}"
                ban_embed.add_field(name="Severity Points Given", value=severity, inline=True)
                ban_embed.add_field(name="Total Severity Points", value=total_severity_points, inline=True)
                ban_embed.set_footer(text="Note: This server invite may not be active when your ban has expired")
                if bot_user.guild_permissions.manage_guild:
                    invites = await server.invites()
                    if len(invites) == 0:
                        ban_embed.add_field(name=f"Invite (For when ban expires)", value=f"Sorry! {ctx.guild.name} does not have any active invites!", inline=False)
                    else:
                        got_indefinite_invite = False
                        longest_invite = invites[0]
                        for invite in invites:
                            if invite.max_age == 0: #If it is indefinite use it
                                ban_embed.add_field(name=f"Invite (For when ban expires)", value=str(invite), inline=False)
                                got_indefinite_invite = True
                                break
                            if invite.max_age > longest_invite.max_age: #Otherwhise we will continue searching for the longest invite
                                longest_invite = invite
                        if not got_indefinite_invite: #Give the longest invite
                            ban_embed.add_field(name=f"Invite (For when ban expires)", value=str(longest_invite), inline=False)
                else:
                    ban_embed.add_field(name=f"Invite (For when ban expires)", value=f"Sorry! Turt bot does not have permission to give out invites!", inline=False)

                if user.dm_channel is None:
                    await user.create_dm()
                    
                await user.dm_channel.send(embed=ban_embed)
                    
                ban_embed.title = f"{user.display_name} has been banned from the server for {bans_strings[ban_level]}."
                ban_embed.set_thumbnail(url=member.avatar_url)
                ban_embed.remove_field(2) #Remove the invite link
                ban_embed.set_footer(text="")


                await ctx.channel.send(embed=ban_embed)

                await ctx.guild.ban(user, reason=reason, delete_message_days=0)

                #Update the database
                self.bot.sql.cursor.execute("UPDATE warnings SET EndTime=? WHERE userid=? AND serverid=?", (end_hour, user_id, ctx.guild.id))
                self.bot.sql.cursor.execute("UPDATE warnings SET severitypoints=? WHERE userid=? AND serverid=?", (total_severity_points, user_id, ctx.guild.id))
                self.bot.sql.conn.commit()



            else:
                await ctx.channel.send(f"Turt bot is unable to ban {user.mention} due to insufficient role status or" +
                                            f" Turt is unable to ban users on this server.\n {user.name} has accumulated " +
                                            f"{total_severity_points} severity points, so it is recommended that {user.name} be banned " +
                                            f"for {bans_strings[ban_level]}.")

        else:
            ban_embed = discord.Embed()
            ban_embed.color = discord.Colour.orange()
            ban_embed.set_author(name=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
            ban_embed.title = f"You have been warned in {ctx.guild.name}."
            ban_embed.description = f"Reason: {reason}"
            ban_embed.add_field(name="Severity Points Given", value=severity, inline=True)
            ban_embed.add_field(name="Total Severity Points", value=total_severity_points, inline=True)
            ban_embed.add_field(name="Ban Punishments", 
                                value="10 severity points: 1 Hour\n" + 
                                    "20 severity points: 1 Day\n" +
                                    "30 severity points: 1 Week\n" + 
                                    "Every 10 severity points afterwards: 1 Month (30 days)",
                                inline=False)

            if user.dm_channel is None:
                await user.create_dm()

            await user.dm_channel.send(embed=ban_embed)

            ban_embed.title = f"{user.display_name} has been warned."
            ban_embed.set_thumbnail(url=user.avatar_url)

            await ctx.channel.send(embed=ban_embed)
            
    @tasks.loop(seconds=60)
    async def check_bans(self):
        await self.bot.wait_until_ready()

        if datetime.now().minute == 0 or self.has_not_checked_bans:
            self.has_not_checked_bans = False

            self.bot.sql.cursor.execute("SELECT * FROM warnings")
        
            warnings = self.bot.sql.cursor.fetchall()
        
            current_time_in_hours = int(time.time()/3600)
        
            user_id_index = 0
            server_id_index = 1
            severity_points_index = 2
            end_time_index = 3
            for warning in warnings:
                                
                end_time = warning[end_time_index]
                if end_time == -1: # This person is not banned
                    continue
        
                user_id = warning[user_id_index]
                server_id = warning[server_id_index]
                if current_time_in_hours - end_time > 0: #Their ban has been lifted because they have served their time
                    #unban
                    user = await self.bot.fetch_user(user_id)
                    server = await self.bot.fetch_guild(server_id)
                    bot_user = await server.fetch_member(self.bot.user.id)
                    if user is None or server is None: 
                        return
                                        
                    #Update EndTime to -1 (Meaning they arent banned now)
                    self.bot.sql.cursor.execute("UPDATE warnings SET EndTime=? WHERE userid=? AND serverid=?", (-1, user_id, server_id))
                    self.bot.sql.conn.commit()

                    # As of right now, you cant dm people who are not in a mutual server. Ill leave this here is case something changes
                    ##Notify via dms
                    #unban_embed = discord.Embed()
                    #unban_embed.color = discord.Colour.dark_green()
                    #unban_embed.title = f"You have served your temporary ban in {server.name}."
                    #unban_embed.add_field(name=f"Total Severity Points in {server.name}", value=warning[severity_points_index], inline=True)
                    #if bot_user.guild_permissions.manage_guild:
                    #    invites = await server.invites()
                    #    if len(invites) == 0:
                    #        unban_embed.add_field(name=f"Invite (For when ban expires)", value=f"Sorry! {ctx.guild.name} does not have any active invites!", inline=False)
                    #    else:
                    #        unban_embed.add_field(name=f"Invite (For when ban expires)", value=str(invites[0]), inline=False) #Gives the first invite
                    #else:
                    #    unban_embed.add_field(name=f"Invite (For when ban expires)", value=f"Sorry! Turt bot does not have permission to give out invites!", inline=False)
                    #unban_embed.add_field(name="Ban Punishments:", 
                    #    value="10 severity points: 1 Hour\n" + 
                    #        "20 severity points: 1 Day\n" +
                    #        "30 severity points: 1 week\n" + 
                    #        "Every 10 severity points afterwards: 1 Month (30 days)",
                    #    inline=False)
                    #unban_embed.set_footer(text="Invite link is single use only.")

                    #if user.dm_channel is None:
                    #    await user.create_dm()

                    #await user.dm_channel.send(embed=unban_embed)

                    await server.unban(user, reason=f"Temporary ban has been served. This user current has {warning[severity_points_index]} severity points.")



def setup(bot: commands.Bot):
    '''Setup the discipline cog'''
    bot.add_cog(Discipline(bot))
