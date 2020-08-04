#import discord.py api wrapper
from discord.ext import commands, tasks
import discord

#import sqlite
import sqlite3
from sqlite3 import Error

from bot.decorators import server_only, whitelist_only, server_owner_only
from bot import constants

# python util
import time
import math
from datetime import datetime
from datetime import timedelta

class Elections(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_votes.start()
        
    @commands.Command
    @server_only()
    @whitelist_only()
    async def allcancallvote(self, ctx, can_all_call_vote:str):
        '''
        Permissions Requirement: Server Whitelisted
        Parameters:
            can_all_call_vote - The new status of whether or not all non-whitelisted users on this server can create elections with `callvote`. Must be `true` or `false`.
        Description:
            Configure whether or not all users on this server will be able to call elections [1].
        Notes:
            [1] It is recommended for this to be set to false in public servers to prevent trolling.
        '''

        #Determine if valid input given
        can_all_call_vote = can_all_call_vote.lower() #Make is case insensitive

        self.bot.sql.cursor.execute("SELECT UsersCanCallVote FROM servers WHERE serverid=?", (ctx.guild.id,))
        result = self.bot.sql.cursor.fetchone()
        if result is None: determine_if_server_exists(ctx.guild.id) #It doesnt, so make it

        #If attempting to allow only whitelisted users create elections
        if can_all_call_vote == "false":
            if result[0] == 1:
                self.bot.sql.cursor.execute("UPDATE servers SET UsersCanCallVote=? WHERE ServerID=?", (0, ctx.guild.id))
                self.bot.sql.conn.commit()
                await ctx.channel.send("Only whitelisted users can create elections now.")
            else:
                await ctx.channel.send("Only whitelisted users were able to create elections.")
                return
        
        #If attempting to allow all users create elections
        elif can_all_call_vote == "true":
            if result[0] == 0:
                self.bot.sql.cursor.execute("UPDATE servers SET UsersCanCallVote=? WHERE ServerID=?", (1, ctx.guild.id))
                self.bot.sql.conn.commit()
                await ctx.channel.send("All users can create elections now.")
            else:
                await ctx.channel.send("All users were able to create elections.")
                return
        else:
                await ctx.channel.send("[can_all_call_vote] must either be 'true' or 'false'.")

    @commands.Command
    @server_only()
    @server_owner_only()
    async def deleteelection(self, ctx, electionid:int):
        '''
        Permissions Requirement: Server Owner
        Parameters:
            electionid - The id of the election to be deleted.
                Election id can be seen in election embeds.
        Description:
            Delete an election from the server. Useful in case of trolling.
        '''

        #Determine if the election is even in this server (or if it even exists)
        self.bot.sql.cursor.execute("SELECT ServerID, MessageID FROM elections WHERE ElectionID=?", (electionid,))
        result = self.bot.sql.cursor.fetchone()
        if result is None or result[0] != ctx.guild.id:
            await ctx.channel.send("No election with that id exists on this server")
            return

        server_id = result[0]
        message_id = result[1]

        #Remove from database
        self.bot.sql.cursor.execute("DELETE FROM elections WHERE ElectionID=?", (electionid,))
        self.bot.sql.conn.commit()

        #Delete the message
        self.bot.sql.cursor.execute("SELECT ElectionChannelID FROM servers WHERE ServerID=?", (result[0],))
        result = self.bot.sql.cursor.fetchone()
        if result is None or result[0] == -1:
            determine_if_server_exists(server_id)
            await ctx.channel.send("Elections are not set up on this server (there cannot be any elections to delete!)")
            return

        channel = await self.bot.sql.fetch_channel(result[0])
        message = await channel.fetch_message(message_id)
        await message.delete()

        await ctx.channel.send("Election successfully removed")

    @commands.Command
    @server_only()
    async def callvote(self, ctx, name:str, desc:str, num_days:int, *argv):
        '''
        Permissions Requirement:
            Server configurations allow all users to create elections: Server Member
            Server configurations allow only whitelisted users to create elections: Server Whitelisted.
        Parameters:
            name - The name of this election.
            desc - An extended description of this election about what it does and what it implies.
            num_days - The number of days this election will be active.
                Minimum of 1 day, decimals allowed.
            argv - All the options for this election up to 10. Each should be in quotations.
                Should not be supplied if this election is to have yes/no options.
        Description:
            Creates an election [3] with the given name and description that lasts for the supplied number of days.
            Users vote in elections by reacting with their choice's emoji. All unrelated emojis are deleted [2].
            Once an election is created, Turt bot will react with all the options (not used in the final vote count).
            Elections can only be called every 24 hours by general users. Whitelisted users and the server owner can create elections without a timeout.
        Notes:
            [1] This is recommended to be restricted from general users in a public server due to spam and trolling.
            [2] Turt must have the manage messages permission to delete emojis.
            [3] The election channel must be set on the server.
        '''

        # Determine if this server allows all users to call votes
        permissions_cog = self.bot.get_cog("Permissions")
        if not permissions_cog.is_whitelisted(ctx.author.id, ctx.guild.id): #If the user is whitelisted, then they will be able to anyway (No need to waste processing power)
            self.bot.sql.cursor.execute("SELECT UsersCanCallVote FROM servers WHERE ServerID=?", (ctx.guild.id,))
            result = self.bot.sql.cursor.fetchone()
            if result is None: 
                determine_if_server_exists(ctx.guild.id)
                await ctx.channel.send("The election channel has not been configured for this server.\n`./t electionchannel [channelID]` to setup election channel.")
                return
            else:
                if result[0] == 0: return #This server does not allow everyone to call elections


        # The election channel must be configured in order to create elections
        self.bot.sql.cursor.execute("SELECT * FROM servers WHERE ServerID=?", (ctx.guild.id,))
        first = self.bot.sql.cursor.fetchone()
        voting_channel_id = None
        if first is None: determine_if_server_exists(ctx.guild.id,) # Add the server to the database if the server does not exist
        else: voting_channel_id = first[1]
        if voting_channel_id is None or voting_channel_id == -1: # Not configured
            await ctx.channel.send("The election channel has not been configured for this server.\n`./t electionchannel [channelID]` to setup election channel.")
            return


        # Make sure the user has not voted in the last 12 hours in any election
        next_time_index = 1 # The index of when the user can create an election next
        current_time_in_hours = int(time.time()/3600) #Round down
        self.bot.sql.cursor.execute("SELECT * FROM users WHERE UserID=?", (ctx.author.id,))# b/c nobody has that userid
        first = self.bot.sql.cursor.fetchone()
        next_time = 0
        if first is None: determine_if_user_exists(ctx.author.id,) #Add the user to the database if they are not there
        else: next_time = first[next_time_index]
        if next_time != None and next_time != "" and next_time != 0 and next_time > current_time_in_hours: #The person has voted in the last 24 hours
            await ctx.channel.send("You can only create an election every 24 hours. You will be able to create an election in " + str(next_time - current_time_in_hours) + " hours.")
            return

        # The user must supply a minimum of 1 day in order to give time for people to vote
        if num_days < 1:
            await ctx.channel.send("An election must go for a minimum of 1 day")
            return


        #Getting time
        hours_in_day = 24
        additional_hours = math.ceil(hours_in_day*(num_days)) #Round up
        endTime = current_time_in_hours + additional_hours # in hours
        endTimeAsDate = datetime.now().replace(microsecond=0, second=0, minute=0) + timedelta(hours=additional_hours) + timedelta(hours=1) #Hours should round up

                
        self.bot.sql.cursor.execute("SELECT MAX(ElectionID) FROM elections") # We want to new id to be the next id not used
        electionID = self.bot.sql.cursor.fetchone()[0]
        if electionID is None: electionID = -1 # If there are no elections right now, then we want to do make the id 0 (Note: adds 1)

        # Getting all the options (If none are given, then this is a yes/no election, not multi option)
        if len(argv) > 10:
            await ctx.channel.send("You can only supply up to 10 choices for an election.")
            return
        multi_option = len(argv) > 0
        options = [None] * 10
        for i in range(len(argv)): #add all this stuff to the new list with length 10
            options[i] = argv[i]

        # Send election message in election channel
        election_embed = discord.Embed()
        election_embed.set_author(name="Initiated by " + ctx.author.display_name, icon_url=ctx.author.avatar_url)
        election_embed.title = "New Election: " + name.title()
        election_embed.description = desc.capitalize()
        if multi_option is False: #not multioption
            election_embed.set_footer(text="Vote by reacting with :thumbsup: or :thumbsdown:")
        else: #Is multioption
            election_embed.set_footer(text="Vote by reacting with the matching number emoji.")
                
        #Time left field
        election_embed.add_field(name="Time Left", value=str(additional_hours) + " Hours", inline=True)

        election_embed.add_field(name="ID", value="`"+str(electionID+1)+"`", inline=True) #We want this as code block to make it look good


        if multi_option is True: #Lets put all the options
            all_options = ""
            for i in range(len(argv)): #TODO: Figure out how to clean this crap up
                number = ":" + constants.numbers[i] + ":"
                all_options += number + " " + argv[i] + "\n"
            election_embed.add_field(name="Options:", value=all_options, inline=False)

        voting_channel = ctx.guild.get_channel(voting_channel_id)
        message = await voting_channel.send(embed=election_embed) #Send it to the voting channel
        #Add all the reactions to the message
        if multi_option is False: #yes/no
            await message.add_reaction(constants.thumbsup.decode())
            await message.add_reaction(constants.thumbsdown.decode())
        if multi_option is True: #Multi option
            for i in range(len(argv)):
                await message.add_reaction(constants.number_emoji_bytes[i])

        # Store the election in the database
        print("Storing")
        self.bot.sql.cursor.execute("INSERT INTO elections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                                                                        (electionID+1, message.id, ctx.guild.id, ctx.author.id, name, desc, endTime, multi_option, 
                                                                                        options[0], options[1], options[2], options[3], options[4], options[5], options[6], options[7], options[8], options[9]))
        self.bot.sql.conn.commit()

        permissions_cog = self.bot.get_cog("Permissions")
        if not permissions_cog.is_whitelisted(ctx.author.id, ctx.guild.id):
            self.bot.sql.cursor.execute("UPDATE users SET WhenCanVoteNext = ? WHERE UserID = ?", (current_time_in_hours+24, ctx.author.id))
            self.bot.sql.conn.commit()

        await ctx.channel.send("Election created! Vote ends in " + str(additional_hours) + " Hours.")

    @commands.Command
    @server_only()
    @whitelist_only()
    async def electionchannel(self, ctx, channelid:int):
        '''Whitelist only.
        Set the channel in which election messages will be sent'''

        if ctx.guild.get_channel(channelid) is not None: #Set the election channel (Must exist on this server)
            self.bot.sql.cursor.execute("UPDATE servers SET ElectionChannelID = ? WHERE ServerID = ?", (channelid, ctx.guild.id))
            self.bot.sql.conn.commit()
            await ctx.channel.send("Election message channel successfully updated to '" + ctx.guild.get_channel(channelid).name + "'")
        else:
            await ctx.channel.send("Channel with id '" + str(channelid) + "' does not exist on this server.")

    @commands.Cog.listener()
    @server_only()
    async def on_raw_reaction_add(self, payload):
        '''Delete all unwanted reactions'''

        # Get message
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        # Determine if the message is a vote message
        embeds = message.embeds
        if message.author.id == self.bot.user.id: 
            if len(embeds) != 0 and embeds[0].title.startswith("New Election"):
                pass
                #This is an election message, neat
            else: #Not an election message
                return 
        else: #Not the bot
            return
                        

        # Determine if the election is a yes/no or a multi-option election
        # Yes/No elections will not have an options field
        election_embed = embeds[0]
        options_field_index = 2
        embeds = message.embeds
        if len(election_embed.fields) >= options_field_index+1 and election_embed.fields[options_field_index].name == "Options:": #This is a multi-option election
            if isinstance(payload.emoji, discord.Emoji): #Elections will never use custom emojis
                await message.clear_reaction(payload.emoji)
                return
            emojis = numbers_emoji_bytes[0:len(election_embed.fields[options_field_index].value.split("\n"))] #Sublist
            if str(payload.emoji).encode() not in emojis: #DELETE IT
                await message.clear_reaction(payload.emoji)
        else: # A Yes/no election
            if isinstance(payload.emoji, discord.Emoji):
                await message.clear_reaction(payload.emoji) #Elections will never use custom emojis
                return
            if str(payload.emoji).encode() != constants.thumbsup and str(payload.emoji).encode() != constants.thumbsdown: #DELETE IT
                await message.clear_reaction(payload.emoji)

    @tasks.loop(seconds=60) 
    async def check_votes(self):
        await self.bot.wait_until_ready()

        #Update the time
        self.bot.sql.cursor.execute("SELECT * FROM elections")
        current_time_in_hours = int(time.time()/3600) # Round down
        election_id_index = 0
        message_id_index = 1
        server_index = 2
        initiating_user_index = 3
        name_index = 4
        desc_index = 5
        end_time_index = 6
        multi_option_indicator_index = 7
        option_start_index = 8
        for row in self.bot.sql.cursor.fetchall():
            #Election info needed to check status and update time
            server_id = row[server_index]
            vote_channel_id = None
            self.bot.sql.cursor.execute("SELECT * FROM servers WHERE ServerID=?", (server_id,))
            result = self.bot.sql.cursor.fetchone()
            if result is None: # The server isnt stored in the database, so add it
                determine_if_server_exists(server_id)
                return
            else: vote_channel_id = result[1]

            if vote_channel_id == -1: return # The server election channel has not been setup yet

            channel = self.bot.get_channel(int(vote_channel_id))
            election_message = await channel.fetch_message(row[message_id_index])

            current_time_in_minutes = int(time.time()/60) # Round it down

            #If the vote is over:
            if int(current_time_in_minutes/60) > row[end_time_index]: #Vote has concluded
                # Send message to channel

                # If the channel isnt set up, then dont do anything for this server (Note that other server elections are in this same list)
                if vote_channel_id == -1: 
                    continue

                # The original election message (so we can get the number of votes for each option or yes/no
                channel = self.bot.get_channel(int(vote_channel_id))
                election_message = await channel.fetch_message(row[message_id_index])


                #To say who initiated the vote, we need to get the member
                user_id = row[initiating_user_index]
                server = await self.bot.fetch_guild(server_id)
                user = await server.fetch_member(user_id)

                winner = "" # The description of the embed

                #Vote conclusion embed message
                vote_embed = discord.Embed()
                vote_embed.title = "Election Concluded: " + row[name_index].title()
                vote_embed.set_author(name="Initiated by " + user.display_name, icon_url=user.avatar_url)
                vote_embed.add_field(name="Description", value=row[desc_index].capitalize(), inline=False)
                if row[multi_option_indicator_index] == 0: #not multioption
                    #Determine the number of votes for yes and no
                    yes=0
                    no=0
        
                    for reaction in election_message.reactions:
                        if reaction.emoji == constants.thumbsup.decode(): 
                            yes = reaction.count
                            if self.bot.user in await reaction.users().flatten():
                                yes = yes-1
                        if reaction.emoji == constants.thumbsdown.decode(): 
                            no = reaction.count
                            if self.bot.user in await reaction.users().flatten():
                                no = no-1
                    
                    if(yes > no): # Note that it has to be a simple majority (tie does not count)
                        winner = "The majority voted :thumbsup:!"
                    elif(yes < no):
                        winner = "The majority voted :thumbsdown:!"
                    elif yes == 0 and no == 0:
                        winner = "Nobody voted!"
                    else:
                        winner = "The vote was a tie!"

                    vote_embed.add_field(name="Yes", value=yes, inline=True)
                    vote_embed.add_field(name="No", value=no, inline=True)
                else: #Multi option
                    #Now we have to grab all the options from the database
                    options = []
                    for i in range(10): #Max options
                        if row[option_start_index + i] is None: #There are no more options to get
                            break
                        else:
                            options.append(row[option_start_index + i])
                                                
                    #Now display the options
                    all_options = ""
                    votes_for_each_option = [0] * len(options)
                    for i in range(len(options)):
                        #Put the right number in front
                        number = ":" + numbers[i] + ":"
                        emoji = numbers_emoji_bytes[i].decode()
                        #Get the number of votes for this option
                        total_votes = 0
                        for reaction in election_message.reactions: #TODO: There has to be a more efficient way to get a specific reaction
                            if reaction.emoji == emoji:
                                total_votes = reaction.count
                                if self.bot.user in await reaction.users().flatten():
                                    total_votes = total_votes - 1
                                break;
                        all_options += number + " " + options[i] + ": `" + str(total_votes) + "`\n"
                        votes_for_each_option[i] = total_votes
                    vote_embed.add_field(name="Options:", value=all_options, inline=False)
                    #Pick the winner (The highest vote count)
                                
                    largest_vote = max(votes_for_each_option) #Highest number
                    if largest_vote == 0:
                        winner = "Nobody voted!"
                    else:
                        # Determine if there is a tie
                        tied = []
                        for i in range(len(votes_for_each_option)):
                            if votes_for_each_option[i] == largest_vote:
                                tied.append(i) #We want to store the index so that we can get it later

                            if len(tied) > 1: #Then there is a tie (There could be a tie between all 10, too)
                                winner = "There was a tie between "
                                for i in tied:
                                    if i == len(tied)-2: #Special formatting to make it look like a sentence
                                        winner += "**'" + options[i] + "**', and "
                                    elif i == len(tied)-1:
                                        winner += "**'" + options[i] + "**'!"
                                    else:
                                        winner += "**'" + options[i] + "**', "
        
                            else: #There is one outright winner
                                winner = "**'" + options[tied[0]].capitalize() + "'** earned the most votes!"#Remember there should only be the largest value in the `tied` list

                vote_embed.description = winner

                vote_embed.set_footer(text="ID: " + str(row[election_id_index]))

                channel = self.bot.get_channel(int(vote_channel_id))
                await channel.send(embed=vote_embed)

                # Remove election from database
                self.bot.sql.cursor.execute("DELETE FROM elections WHERE ElectionID=?", (row[election_id_index],))
                self.bot.sql.conn.commit()

                # Delete original message (All information from it is in the conclusion message, so nothing is lost
                channel = self.bot.get_channel(int(vote_channel_id))
                election_message = await channel.fetch_message(row[message_id_index])
                await election_message.delete()
                                
                return #It has ended

            # The thing has not ended, so we should update the time until it does

            #Update time
            time_left = row[end_time_index] - math.ceil(current_time_in_minutes/60) # Round up

            message = ""
            if time_left < 1:
                message = str((row[end_time_index]*60 - current_time_in_minutes) - 60*time_left) + " Minutes"
            else:
                message = str(time_left) + " Hours, " + str((row[end_time_index]*60 - current_time_in_minutes) - 60*time_left) + " Minutes"

            embed = election_message.embeds[0]
            embed.set_field_at(index=0, name="Time Left", value=message, inline=True)
            await election_message.edit(embed=embed)

    async def delete_unwanted_election_reactions(self):
        self.bot.sql.cursor.execute("SELECT ElectionChannelID FROM servers")
        for election_channel_id in self.bot.sql.cursor.fetchall(): #Iterate through all the voting channels
            election_channel_id = election_channel_id[0]
            if election_channel_id == -1: return # The server does not have the election channel set up, so ignore it
            channel = await self.bot.fetch_channel(election_channel_id)
            self.bot.sql.cursor.execute("SELECT MessageID FROM elections")
            for election_message_id in self.bot.sql.cursor.fetchall(): #Get each message ID
                election_message_id = election_message_id[0]
                try:
                    message = await channel.fetch_message(election_message_id)
                    if message.author != self.bot.user.id: continue # If the message does not belong to this bot, then dont worry about it
                    reactions = message.reactions
                    options_field_index = 2
                    embeds = message.embeds
                    election_embed = embeds[0]
                    if len(election_embed.fields) >= options_field_index+1 and election_embed.fields[options_field_index].name == "Options:": #This is a multi-option election
                        for reaction in reactions:
                            if isinstance(reaction.emoji, discord.Emoji): 
                                await reaction.clear() #Elections will never use custom emojis
                                continue
                            emojis = numbers_emoji_bytes[0:len(election_embed.fields[options_field_index].value.split("\n"))] #Sublist
                            if reaction.emoji.encode() not in emojis: #DELETE IT
                                await reaction.clear()
                    else: # A Yes/no election
                        for reaction in reactions:
                            if isinstance(reaction.emoji, discord.Emoji): 
                                await reaction.clear() #Elections will never use custom emojis
                            elif reaction.emoji.encode() != constants.thumbsup and reaction.emoji.encode() != constants.thumbsdown: #DELETE IT
                                await reaction.clear()
                except Exception as e:
                    pass

def setup(bot: commands.Bot) -> None:
        '''Load the elections cog'''
        bot.add_cog(Elections(bot))
