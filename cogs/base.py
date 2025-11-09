#***************************************************************************#
# FloofBot
#***************************************************************************#

import discord
import platform
import random
import json
import json5
import os

from discord.ext import commands
from random import randint

# Files for bot data and configuration
DB_FILE = 'db.json'
CONFIG_FILE = 'config.json5'

# Load configuration data
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r') as f:
        return json5.load(f)

def get_setting(key, default=None):
    config = load_config()
    return config.get(key, default)

# Get owner ID from config
ownerID = get_setting('owner_id', 0)

class Base(commands.Cog):

    """Cog for Base commands"""

    def __init__(self, bot):
        self.bot = bot

    #Ping Command
    @commands.slash_command(description="Ping pong")
    async def ping(self, ctx):
        await ctx.respond("Pong")
    
    #Server Command
    @commands.slash_command(descriptin="Shows server info")
    async def server(self, ctx):
        server = ctx.guild
        icon = ("\uFEFF")
        embed = discord.Embed(
            title=f"Server info for {server.name}",
            description='\uFEFF',
            colour=0x98FB98)
        try:
            embed.set_thumbnail(url=server.icon(size=512))
        except:
            pass
        embed.add_field(name="Name", value=server.name, inline=True)
        embed.add_field(name="Member Count", value=server.member_count, inline=True)
        embed.add_field(name="Owner", value="<@" + f"{server.owner_id}" + ">", inline=True)
        embed.add_field(name="ID", value=server.id, inline=True)
        embed.add_field(name="Creation Date", value=f"{server.created_at}", inline=True)
        embed.set_footer(text=f"Ran by: {ctx.author} • Yours truly, Poggers")
        await ctx.respond(content=None, embed=embed)

    #Stats Command
    @commands.slash_command()
    async def stats(self, ctx):

        pythonVersion = platform.python_version()
        dpyVersion = discord.__version__
        serverCount = len(self.bot.guilds)
        memberCount = len(set(self.bot.get_all_members()))

        embed = discord.Embed(
            title=f'FloofBot Stats',
            description='\uFEFF',
            colour=0x98FB98)

        embed.add_field(
            name='Python Version:', value=f"{pythonVersion}", inline=False)
        embed.add_field(
            name='Py-Cord Version', value=f"{dpyVersion}", inline=False)
        embed.add_field(name='Total Guilds:', value=f"{serverCount}", inline=False)
        embed.add_field(name='Total Users:', value=f"{memberCount}", inline=False)
        embed.add_field(name='Bot Developer:', value="<@" + f"{ownerID}" + ">", inline=False)
        embed.set_footer(text=f"Ran by: {ctx.author} • Yours truly, Poggers")
        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def channelid(self, ctx):
        await ctx.respond(str(ctx.channel.id))

    @commands.slash_command(brief="Get the ID of a member")
    async def userid(self, ctx, member : discord.Member=0):
      if member == 0:
        await ctx.respond(str(ctx.author.id))
      else:
        await ctx.respond(str(member.id))

    @commands.slash_command(description="Display all bot commands organized by category")
    async def help(self, ctx, category: str = None):
        """Display all bot commands organized by cog"""
        
        # Define cog descriptions and emojis
        cog_info = {
            "Base": {"emoji": "⚙️", "description": "Basic bot commands and utilities"},
            "MarioParty": {"emoji": "🎮", "description": "Mario Party game and board selection"},
            "Fun": {"emoji": "🎉", "description": "Fun and entertainment commands"},
            "Leveling": {"emoji": "📊", "description": "XP and leveling system"},
            "Birthday": {"emoji": "🎂", "description": "Birthday tracking and celebrations"},
            "Quotes": {"emoji": "💬", "description": "Save and retrieve memorable quotes"},
            "Music": {"emoji": "🎵", "description": "Music playback and queue management"},
            "SwitchFriendCodes": {"emoji": "🎮", "description": "Nintendo Switch friend code management"}
        }
        
        if category:
            # Show specific category
            cog = self.bot.get_cog(category)
            if not cog:
                await ctx.respond(f"❌ Category '{category}' not found! Use `/help` to see all categories.")
                return
            
            info = cog_info.get(category, {"emoji": "📁", "description": "Bot commands"})
            
            # Get all commands for this cog
            commands_list = []
            
            # Regular slash commands
            for command in cog.walk_commands():
                if isinstance(command, discord.SlashCommand):
                    cmd_desc = command.description or "No description"
                    commands_list.append(f"**/{command.name}** - {cmd_desc}")
            
            # Slash command groups (like /board)
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if isinstance(attr, discord.SlashCommandGroup):
                    # Add the group itself
                    group_desc = attr.description or "Command group"
                    commands_list.append(f"\n**/{attr.name}** - {group_desc}")
                    
                    # Add subcommands
                    for subcommand in attr.walk_commands():
                        sub_desc = subcommand.description or "No description"
                        commands_list.append(f"  ├─ **/{attr.name} {subcommand.name}** - {sub_desc}")
            
            if not commands_list:
                embed = discord.Embed(
                    title=f"{info['emoji']} {category} Commands",
                    description=info['description'],
                    colour=0x98FB98
                )
                embed.add_field(name="Commands", value="No commands available", inline=False)
                embed.set_footer(text=f"Ran by: {ctx.author} • Use /help to see all categories")
                await ctx.respond(embed=embed)
                return
            
            # Split commands into chunks that fit within Discord's 1024 character limit
            embeds = []
            current_chunk = []
            current_length = 0
            
            for cmd in commands_list:
                cmd_length = len(cmd) + 1  # +1 for newline
                
                # If adding this command would exceed the limit, start a new chunk
                if current_length + cmd_length > 1000:  # Use 1000 to be safe
                    embeds.append("\n".join(current_chunk))
                    current_chunk = [cmd]
                    current_length = cmd_length
                else:
                    current_chunk.append(cmd)
                    current_length += cmd_length
            
            # Add the last chunk
            if current_chunk:
                embeds.append("\n".join(current_chunk))
            
            # Send the first embed as a response
            first_embed = discord.Embed(
                title=f"{info['emoji']} {category} Commands",
                description=info['description'],
                colour=0x98FB98
            )
            first_embed.add_field(name="Commands" + (" (Part 1)" if len(embeds) > 1 else ""), value=embeds[0], inline=False)
            first_embed.set_footer(text=f"Ran by: {ctx.author} • Use /help to see all categories")
            await ctx.respond(embed=first_embed)
            
            # Send additional embeds as follow-up messages
            for i, chunk in enumerate(embeds[1:], start=2):
                follow_embed = discord.Embed(
                    title=f"{info['emoji']} {category} Commands (Part {i})",
                    colour=0x98FB98
                )
                follow_embed.add_field(name="Commands (continued)", value=chunk, inline=False)
                follow_embed.set_footer(text=f"Ran by: {ctx.author} • Use /help to see all categories")
                await ctx.send(embed=follow_embed)
        else:
            # Show all categories
            embed = discord.Embed(
                title="🤖 The Underground Grotto Bot - Help",
                description="Here are all available command categories. Use `/help [category]` to see commands in that category.",
                colour=0x98FB98
            )
            
            # Group commands by cog
            for cog_name, cog in self.bot.cogs.items():
                info = cog_info.get(cog_name, {"emoji": "📁", "description": "Bot commands"})
                
                # Count commands in this cog
                command_count = 0
                for command in cog.walk_commands():
                    command_count += 1
                
                # Count command groups
                for attr_name in dir(cog):
                    attr = getattr(cog, attr_name)
                    if isinstance(attr, discord.SlashCommandGroup):
                        command_count += 1
                
                if command_count > 0:
                    embed.add_field(
                        name=f"{info['emoji']} {cog_name}",
                        value=f"{info['description']}\n`/help {cog_name}` ({command_count} command{'s' if command_count != 1 else ''})",
                        inline=False
                    )
            
            embed.set_footer(text=f"Ran by: {ctx.author} • Yours truly, The Underground Grotto Bot")
            await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Base(bot))