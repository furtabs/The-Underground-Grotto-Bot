import discord
from discord.ext import commands
import json
import os
import random

DB_FILE = 'db.json'

def load_db():
    if not os.path.exists(DB_FILE):
        return {"quotes": [], "birthdays": {}, "levels": {}}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_quotes():
    data = load_db()
    return data.get('quotes', [])

def save_quotes(quotes):
    data = load_db()
    data['quotes'] = quotes
    save_db(data)

class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='quote', description='Save a quote by replying to a message.')
    async def quote(self, ctx: discord.ApplicationContext):
        # Attempt to get the message being replied to
        ref_data = ctx.interaction.data.get("resolved", {}).get("messages")
        if not ref_data:
            await ctx.respond('Please use this command by replying to a message.', ephemeral=True)
            return

        # Get the first replied message (should only be one)
        message_id, message_payload = next(iter(ref_data.items()))
        try:
            quoted_message = await ctx.channel.fetch_message(int(message_id))
        except discord.NotFound:
            await ctx.respond('Could not find the referenced message.', ephemeral=True)
            return

        quotes = load_quotes()
        quote_entry = {
            'content': quoted_message.content,
            'author': str(quoted_message.author),
            'author_id': quoted_message.author.id,
            'saved_by': str(ctx.author),
            'saved_by_id': ctx.author.id,
            'channel_id': ctx.channel.id,
            'guild_id': ctx.guild.id
        }
        quotes.append(quote_entry)
        save_quotes(quotes)
        await ctx.respond('Quote saved!', ephemeral=True)

    @commands.slash_command(name='quotes', description='Show a random saved quote.')
    async def quotes(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        """Show a random quote, optionally filtered by user."""
        quotes = load_quotes()
        if not quotes:
            await ctx.respond('No quotes saved yet!')
            return
        
        # Filter by user if specified
        if user:
            user_quotes = [q for q in quotes if q['author_id'] == user.id]
            if not user_quotes:
                await ctx.respond(f'No quotes saved from {user.display_name} yet!')
                return
            quote = random.choice(user_quotes)
            embed = discord.Embed(
                description=quote['content'], 
                color=discord.Color.purple(),
                title=f"Quote from {user.display_name}"
            )
            embed.set_author(name=f"{quote['author']}", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.set_footer(text=f"Saved by {quote['saved_by']} • {len(user_quotes)} total quote{'s' if len(user_quotes) != 1 else ''}")
        else:
            quote = random.choice(quotes)
            embed = discord.Embed(description=quote['content'], color=discord.Color.purple())
            embed.set_author(name=f"{quote['author']}")
            embed.set_footer(text=f"Saved by {quote['saved_by']}")
        
        await ctx.respond(embed=embed)

    @commands.user_command(name="Get Random Quote")
    async def get_user_quote(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Right-click menu command to get a random quote from a user."""
        quotes = load_quotes()
        
        if not quotes:
            await ctx.respond('No quotes saved yet!', ephemeral=True)
            return
        
        # Filter quotes by this user
        user_quotes = [q for q in quotes if q['author_id'] == user.id]
        
        if not user_quotes:
            await ctx.respond(f'No quotes saved from {user.display_name} yet!', ephemeral=True)
            return
        
        # Show a random quote from this user
        quote = random.choice(user_quotes)
        embed = discord.Embed(
            description=quote['content'], 
            color=discord.Color.purple(),
            title=f"Quote from {user.display_name}"
        )
        embed.set_author(name=f"{quote['author']}", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.set_footer(text=f"Saved by {quote['saved_by']} • {len(user_quotes)} total quote{'s' if len(user_quotes) != 1 else ''}")
        
        await ctx.respond(embed=embed)

    @commands.message_command(name="Save as Quote")
    async def save_message_as_quote(self, ctx: discord.ApplicationContext, message: discord.Message):
        """Right-click context menu command to save a message as a quote."""
        
        # Don't save empty messages or bot messages
        if not message.content or message.author.bot:
            await ctx.respond('Cannot save this message as a quote!', ephemeral=True)
            return
        
        quotes = load_quotes()
        
        # Check if this exact quote already exists
        for q in quotes:
            if q['content'] == message.content and q['author_id'] == message.author.id:
                await ctx.respond('This quote has already been saved!', ephemeral=True)
                return
        
        # Save the quote
        quote_entry = {
            'content': message.content,
            'author': str(message.author),
            'author_id': message.author.id,
            'saved_by': str(ctx.author),
            'saved_by_id': ctx.author.id,
            'channel_id': ctx.channel.id,
            'guild_id': ctx.guild.id
        }
        quotes.append(quote_entry)
        save_quotes(quotes)
        
        # Show confirmation with the saved quote
        embed = discord.Embed(
            title="✅ Quote Saved!",
            description=message.content,
            color=discord.Color.green()
        )
        embed.set_author(name=f"{message.author.display_name}", icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        embed.set_footer(text=f"Saved by {ctx.author.display_name}")
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(Quotes(bot))
