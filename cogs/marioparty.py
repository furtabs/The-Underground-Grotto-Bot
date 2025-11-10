#***************************************************************************#
#                                                                           #
# Underground Grotto Bot                                                    #
# Mario Party Commands                                                      #
# Copyright (C) 2024-2025 Tabitha Hanegan. All rights reserved.            #
#                                                                           #
# License:                                                                  #
# MIT License https://www.mit.edu/~amini/LICENSE.md                         #
#                                                                           #
#***************************************************************************#

import discord
import urllib
import asyncio
from discord.ext import commands
from discord import SlashCommandGroup
from discord.ui import Modal
from util.wheel import generate_wheel_gif

class MarioParty(commands.Cog):

    """Cog for Mario Party commands"""

    def __init__(self, bot):
        self.bot = bot
        # Store eliminated boards per channel and game
        # Format: {channel_id: {game_name: [eliminated_boards]}}
        self.eliminated_boards = {}
        # Store eliminated games per channel
        # Format: {channel_id: {category: [eliminated_games]}}
        self.eliminated_games = {}

    board = SlashCommandGroup("board", "MP Board related commands")


    async def spin_wheel_and_show_result(self, ctx, options, title, description, image_path=None, filename=None):
        """Generic function to spin wheel and show result with embed."""
        # Defer immediately to avoid interaction timeout
        await ctx.defer()
        
        # Use the wheel system - get both GIF and final image
        selected, gif_io, _ = generate_wheel_gif(options)

        # Send the GIF as a follow-up
        gif_file = discord.File(gif_io, "spinning_wheel.gif")
        message = await ctx.followup.send(file=gif_file)

        # Wait for suspense
        await asyncio.sleep(5)

        # Delete the GIF message
        await message.delete()
        
        # Generate final wheel with ONLY the winner (like elimination results)
        _, _, final_img_io = generate_wheel_gif([selected])
        
        # Create embed with the final wheel - all in one
        final_image_file = discord.File(final_img_io, "final_wheel.png")
        result_embed = discord.Embed(
            title=f"🏆 WINNER: {selected}!",
            description=title,
            colour=0x98FB98
        )
        result_embed.set_image(url="attachment://final_wheel.png")
        result_embed.set_footer(text=f"Ran by: {ctx.author} • Yours truly, The Underground Grotto Bot")
        
        # Send everything in one message as follow-up
        await ctx.followup.send(embed=result_embed, file=final_image_file)

    async def spin_game_wheel(self, ctx, gameList, category_name):
        """Helper function to spin the wheel for game selection with elimination."""
        channel_id = ctx.channel.id
        
        # Initialize channel tracking if needed
        if channel_id not in self.eliminated_games:
            self.eliminated_games[channel_id] = {}
        
        # Initialize category tracking if needed
        if category_name not in self.eliminated_games[channel_id]:
            self.eliminated_games[channel_id][category_name] = []
        
        # Get remaining games (not eliminated)
        eliminated = self.eliminated_games[channel_id][category_name]
        remaining_games = [game for game in gameList if game not in eliminated]
        
        # Check if we need to reset (all games have been eliminated)
        if len(remaining_games) == 0:
            self.eliminated_games[channel_id][category_name] = []
            remaining_games = gameList.copy()
            await ctx.respond("🔄 All games have been played! Starting new elimination round...", delete_after=3)
            await asyncio.sleep(2)
        
        # Initial response
        total_games = len(remaining_games)
        await ctx.respond(f"🎲 Starting elimination process with {total_games} game{'s' if total_games != 1 else ''}!", delete_after=3)
        await asyncio.sleep(2)
        
        # Keep spinning until only 1 game remains
        while len(remaining_games) > 1:
            # Generate GIF & final static image with remaining games
            selected_game, gif_io, final_img_io = generate_wheel_gif(remaining_games)
            
            # Eliminate the selected game
            self.eliminated_games[channel_id][category_name].append(selected_game)
            remaining_games = [game for game in remaining_games if game != selected_game]
            
            games_left = len(remaining_games)
            
            # Send the GIF
            gif_file = discord.File(gif_io, "spinning_wheel.gif")
            status_msg = await ctx.send(f"🎯 Spinning... ({int(games_left + 1)} game{'s' if games_left != 1 else ''} remaining)")
            gif_msg = await ctx.send(file=gif_file)

            # Wait for suspense
            await asyncio.sleep(5)

            # Delete the GIF and status messages
            await gif_msg.delete()
            await status_msg.delete()

            # Send the elimination result
            result_embed = discord.Embed(
                title=f"❌ Eliminated: {selected_game}",
                description=f"**{games_left}** game{'s' if games_left != 1 else ''} remaining",
                colour=0xFF6B6B
            )
            result_embed.set_footer(text=f"Continuing elimination...")
            await ctx.send(embed=result_embed)
            
            # Small delay before next spin (unless it's the last one)
            if games_left > 1:
                await asyncio.sleep(3)
        
        # Final winner announcement
        winner = remaining_games[0]
        
        # Generate final wheel with just the winner
        _, _, final_img_io = generate_wheel_gif([winner])
        
        final_image_file = discord.File(final_img_io, "final_wheel.png")
        
        winner_embed = discord.Embed(
            title=f"🏆 WINNER: {winner}!",
            description=f"**The last game standing!**\nThis is your game for today!",
            colour=0x98FB98
        )
        winner_embed.set_image(url="attachment://final_wheel.png")
        winner_embed.set_footer(text=f"Ran by: {ctx.author} • Yours truly, The Underground Grotto Bot")
        
        await ctx.send(embed=winner_embed, file=final_image_file)
        
        # Reset for next time
        self.eliminated_games[channel_id][category_name] = []

    # Game selection commands
    @commands.slash_command(name="pickgame", description="Random Mario Party game")
    async def pickgame(self, ctx):
        games = [f"Mario Party {i}" for i in range(1, 9)]
        await self.spin_game_wheel(ctx, games, "all_games")

    @commands.slash_command(name="pickgcwii", description="Random GC/Wii Mario Party game")
    async def pickgcwii(self, ctx):
        games = [f"Mario Party {i}" for i in range(4, 9)]
        await self.spin_game_wheel(ctx, games, "gcwii_games")

    @commands.slash_command(name="pickn64", description="Random N64 Mario Party game")
    async def pickn64(self, ctx):
        games = [f"Mario Party {i}" for i in range(1, 4)]
        await self.spin_game_wheel(ctx, games, "n64_games")

    # Game mode commands
    @commands.slash_command(name="picknormalgamemode", description="Random normal game mode")
    async def picknormalgamemode(self, ctx):
        modes = ["Mario Party: Magic Conch", "Mario Party: Simon Says", "Mario Party: Raiders Wrath", "Mario Party: Inversal Reversal", "Mario Party Mayhem: Hot Potato Havoc"]
        await self.spin_wheel_and_show_result(ctx, modes, "🎯 Normal Game Mode Selected!", "normal game mode")

    @commands.slash_command(name="pickmayhemgamemode", description="Random mayhem game mode")
    async def pickmayhemgamemode(self, ctx):
        modes = ["Mario Party Mayhem: Classic", "Mario Party Mayhem: Modern", "Mario Party Mayhem: Magic Conch", "Mario Party Mayhem: Mayhem Says", "Mario Party Mayhem: Raiders Wrath", "Mario Party Mayhem: Inversal Reversal", "Mario Party Mayhem: Hot Potato Havoc"]
        await self.spin_wheel_and_show_result(ctx, modes, "🎯 Mayhem Game Mode Selected!", "mayhem game mode")

    @commands.slash_command(name="pickdxmode", description="Random Mario Party version")
    async def pickDXmode(self, ctx):
        modes = ["Vanilla", "DX"]
        await self.spin_wheel_and_show_result(ctx, modes, "🎯 Mario Party Version Selected!", "DX or vanilla version")

    @commands.slash_command(name="pickmpmode", description="Random Mario Party mode")
    async def pickMPmode(self, ctx):
        modes = ["Vanilla", "Mayhem"]
        await self.spin_wheel_and_show_result(ctx, modes, "🎮 Mario Party Mode Selected!", "Mario Party mode")

    # Settings commands
    @commands.slash_command(name="bonusstars", description="Random bonus stars setting")
    async def bstars(self, ctx):
        options = ["Off", "On", "Ztars"]
        await self.spin_wheel_and_show_result(ctx, options, "⭐ Bonus Stars Setting Selected!", "bonus stars setting")

    @commands.slash_command(name="duels", description="Samee space duels")
    async def samespaceduels(self, ctx):
        options = ["Always", "Vanilla", "Never"]
        await self.spin_wheel_and_show_result(ctx, options, "⚔️ Same Space Duels Setting Selected!", "duels setting")

    @commands.slash_command(name="gentlemans", description="Random gentleman's rule setting")
    async def gentlemans(self, ctx):
        options = ["On", "Off"]
        await self.spin_wheel_and_show_result(ctx, options, "🎩 Gentleman's Rule Setting Selected!", "gentlemans rule setting")

    @commands.slash_command(name="stealchoice", description="Random steal choice setting")
    async def stealduels(self, ctx):
        options = ["Choose", "Random"]
        await self.spin_wheel_and_show_result(ctx, options, "🎯 Steal Choice Setting Selected!", "steal choice setting")

    @commands.slash_command(name="duelchoice", description="Random duel choice setting")
    async def stealduel(self, ctx):
        options = ["Choose", "Random"]
        await self.spin_wheel_and_show_result(ctx, options, "🎯 Duel Choice Setting Selected!", "duel choice setting")

    async def spin_board_wheel(self, ctx, boardList, game_name):
        """Helper function to spin the wheel for any Mario Party game board with elimination."""
        channel_id = ctx.channel.id
        
        # Initialize channel tracking if needed
        if channel_id not in self.eliminated_boards:
            self.eliminated_boards[channel_id] = {}
        
        # Initialize game tracking if needed
        if game_name not in self.eliminated_boards[channel_id]:
            self.eliminated_boards[channel_id][game_name] = []
        
        # Get remaining boards (not eliminated)
        eliminated = self.eliminated_boards[channel_id][game_name]
        remaining_boards = [board for board in boardList if board not in eliminated]
        
        # Check if we need to reset (all boards have been eliminated)
        if len(remaining_boards) == 0:
            self.eliminated_boards[channel_id][game_name] = []
            remaining_boards = boardList.copy()
            await ctx.respond("🔄 All boards have been played! Starting new elimination round...", delete_after=3)
            await asyncio.sleep(2)
        
        # Initial response
        total_boards = len(remaining_boards)
        await ctx.respond(f"🎲 Starting elimination process with {total_boards} boards!", delete_after=3)
        await asyncio.sleep(2)
        
        # Keep spinning until only 1 board remains
        while len(remaining_boards) > 1:
            # Generate GIF & final static image with remaining boards
            selected_board, gif_io, final_img_io = generate_wheel_gif(remaining_boards)
            
            # Eliminate the selected board
            self.eliminated_boards[channel_id][game_name].append(selected_board)
            remaining_boards = [board for board in remaining_boards if board != selected_board]
            
            boards_left = len(remaining_boards)
            
            # Send the GIF
            gif_file = discord.File(gif_io, "spinning_wheel.gif")
            status_msg = await ctx.send(f"🎯 Spinning... ({boards_left} board{'s' if boards_left != 1 else ''} remaining)")
            gif_msg = await ctx.send(file=gif_file)

            # Wait for suspense
            await asyncio.sleep(5)

            # Delete the GIF and status messages
            await gif_msg.delete()
            await status_msg.delete()

            # Send the elimination result
            result_embed = discord.Embed(
                title=f"❌ Eliminated: {selected_board}",
                description=f"**{boards_left}** board{'s' if boards_left != 1 else ''} remaining",
                colour=0xFF6B6B
            )
            result_embed.set_footer(text=f"Continuing elimination...")
            await ctx.send(embed=result_embed)
            
            # Small delay before next spin (unless it's the last one)
            if boards_left > 1:
                await asyncio.sleep(3)
        
        # Final winner announcement
        winner = remaining_boards[0]
        
        # Try to load the board image
        board_image_path = f"boards/{game_name}/{winner}.png"
        board_file = None
        
        try:
            board_file = discord.File(board_image_path, filename="board.png")
            winner_embed = discord.Embed(
                title=f"🏆 WINNER: {winner}!",
                description=f"**The last board standing!**\nThis is your board for today!",
                colour=0x98FB98
            )
            winner_embed.set_image(url="attachment://board.png")
            winner_embed.set_footer(text=f"Ran by: {ctx.author} • Yours truly, The Underground Grotto Bot")
            
            await ctx.send(embed=winner_embed, file=board_file)
        except FileNotFoundError:
            # Fallback to wheel if board image not found
            _, _, final_img_io = generate_wheel_gif([winner])
            final_image_file = discord.File(final_img_io, "final_wheel.png")
            
            winner_embed = discord.Embed(
                title=f"🏆 WINNER: {winner}!",
                description=f"**The last board standing!**\nThis is your board for today!",
                colour=0x98FB98
            )
            winner_embed.set_image(url="attachment://final_wheel.png")
            winner_embed.set_footer(text=f"Ran by: {ctx.author} • Yours truly, The Underground Grotto Bot")
            
            await ctx.send(embed=winner_embed, file=final_image_file)
        
        # Reset for next time
        self.eliminated_boards[channel_id][game_name] = []

    @board.command(name='1')
    async def one(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 1 board."""
        boardList = [
            "DK's Jungle Adventure", "Peach's Birthday Cake", "Yoshi's Tropical Island", 
            "Mario's Rainbow Castle", "Wario's Battle Canyon", "Luigi's Engine Room", 
            "Eternal Star", "Bowser's Magma Mountain"
        ]
        await self.spin_board_wheel(ctx, boardList, "1")

    @board.command(name='2')
    async def two(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 2 board."""
        boardList = [
            "Western Land", "Space Land", "Mystery Land", 
            "Pirate Land", "Horror Land", "Bowser Land"
        ]
        await self.spin_board_wheel(ctx, boardList, "2")

    @board.command(name='3')
    async def three(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 3 board."""
        boardList = [
            "Chilly Waters", "Deep Bloober Sea", "Woody Woods", 
            "Creepy Cavern", "Spiny Desert", "Waluigi's Island"
        ]
        await self.spin_board_wheel(ctx, boardList, "3")

    @board.command(name='4')
    async def four(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 4 board."""
        boardList = [
            "Toad's Midway Madness", "Boo's Haunted Bash", "Koopa's Seaside Soiree", 
            "Goomba's Greedy Gala", "Shy Guy's Jungle Jam", "Bowser's Gnarly Party"
        ]
        await self.spin_board_wheel(ctx, boardList, "4")

    @board.command(name='5')
    async def five(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 5 board."""
        boardList = [
            "Toy Dream", "Rainbow Dream", "Pirate Dream", 
            "Future Dream", "Undersea Dream", "Sweet Dream", "Bowser's Nightmare"
        ]
        await self.spin_board_wheel(ctx, boardList, "5")

    @board.command(name='6')
    async def six(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 6 board."""
        boardList = [
            "Towering Treetop", "E Gadd's Garage", "Faire Square", 
            "Snowflake Lake", "Castaway Bay", "Clockwork Castle"
        ]
        await self.spin_board_wheel(ctx, boardList, "6")

    @board.command(name='7')
    async def seven(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 7 board."""
        boardList = [
            "Grand Canal", "Pagoda Peak", "Pyramid Park", 
            "Neon Heights", "Windmillville", "Bowser's Enchanted Inferno"
        ]
        await self.spin_board_wheel(ctx, boardList, "7")

    @board.command(name='8')
    async def eight(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 8 board."""
        boardList = [
            "DK's Treetop Temple", "Goomba's Booty Boardwalk", "King Boo's Haunted Hideaway", 
            "Shy Guy's Perplex Express", "Koopa's Tycoon Town", "Bowser's Warped Orbit"
        ]
        await self.spin_board_wheel(ctx, boardList, "8")

    @board.command(name='9')
    async def nine(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 9 board."""
        boardList = [
            "Toad Road", "Blooper Beach", "Boo's Horror Castle", 
            "DK's Jungle Ruins", "Bowser's Station", "Magma Mine", "Bob-omb Factory"
        ]
        await self.spin_board_wheel(ctx, boardList, "9")

    @board.command(name='10')
    async def ten(self, ctx):
        """Spins a wheel to randomly pick a Mario Party 10 board."""
        boardList = ["Mushroom Park", "Whimsical Waters", "Chaos Castle", "Airship Central", "Haunted Trail"]
        await self.spin_board_wheel(ctx, boardList, "10")

    @board.command()
    async def ds(self, ctx):
        """Spins a wheel to randomly pick a Mario Party DS board."""
        boardList = ["Wiggler's Garden", "Kamek's Library", "Bowser's Pinball Machine", "Toadette's Music Room", "DK's Stone Statue"]
        await self.spin_board_wheel(ctx, boardList, "DS")

    @board.command(name='super')
    async def super(self, ctx):
        """Spins a wheel to randomly pick a Super Mario Party board."""
        boardList = ["Whomp's Domino Ruins", "King Bob-omb's Powderkeg Mine", "Megafruit Paradise", "Kamek's Tantalizing Tower"]
        await self.spin_board_wheel(ctx, boardList, "Super")

    @board.command(name='superstars')
    async def superstars(self, ctx):
        """Spins a wheel to randomly pick a Mario Party Superstars board."""
        boardList = ["Yoshi's Tropical Island", "Peach's Birthday Cake", 'Space Land', 'Horror Land', 'Woody Woods']
        await self.spin_board_wheel(ctx, boardList, "Superstars")

    @board.command(name='jamboree')
    async def jamboree(self, ctx):
        """Spins a wheel to randomly pick a Super Mario Party Jamboree board."""
        boardList = [
            "Mega Wiggler's Tree Party", "Rainbow Galleria", 'Goomba Lagoon', 
            "Roll\'em Raceway", 'Western Land', "Mario\'s Rainbow Castle", "King Bowser\'s Keep"
        ]
        await self.spin_board_wheel(ctx, boardList, "Jamboree")

    @commands.slash_command(name='wheel', description="Spin a wheel with custom options")
    async def wheel(self, ctx):
        """Shows a modal to input wheel options."""
        modal = WheelModal(self)
        await ctx.send_modal(modal)


class WheelModal(Modal):
    """Modal for entering wheel options."""
    
    def __init__(self, cog):
        super().__init__(title="Wheel Options")
        self.cog = cog
        self.options_input = discord.ui.TextInput(
            label="Options (comma-separated)",
            placeholder="1, 2, 3",
            style=discord.InputTextStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.options_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        options_text = self.options_input.value.strip()
        
        if not options_text:
            await interaction.response.send_message("❌ Please provide at least one option!", ephemeral=True)
            return
        
        # Split by comma and clean up
        filter_options = [option.strip() for option in options_text.split(',') if option.strip()]
        
        if not filter_options:
            await interaction.response.send_message("❌ Please provide at least one valid option!", ephemeral=True)
            return
        
        if len(filter_options) < 2:
            await interaction.response.send_message("❌ Please provide at least 2 options for the wheel!", ephemeral=True)
            return
        
        # Defer the response since we'll be sending multiple messages
        await interaction.response.defer()
        
        # Create a minimal context-like object for compatibility
        class InteractionContext:
            def __init__(self, inter):
                self.interaction = inter
                self.author = inter.user
                self.channel = inter.channel
                
            async def respond(self, content=None, **kwargs):
                """Respond using followup after defer."""
                return await self.interaction.followup.send(content=content, **kwargs)
            
            async def send(self, content=None, **kwargs):
                """Send message using followup."""
                return await self.interaction.followup.send(content=content, **kwargs)
        
        ctx = InteractionContext(interaction)
        await self.cog.spin_wheel_and_show_result(ctx, filter_options, f"🎉 The wheel landed on!", "custom wheel")

def setup(bot):
    bot.add_cog(MarioParty(bot))