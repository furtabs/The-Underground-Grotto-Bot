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
    async def quotes(self, ctx: discord.ApplicationContext):
        quotes = load_quotes()
        if not quotes:
            await ctx.respond('No quotes saved yet!')
            return
        quote = random.choice(quotes)
        embed = discord.Embed(description=quote['content'], color=discord.Color.purple())
        embed.set_author(name=f"{quote['author']}")
        embed.set_footer(text=f"Saved by {quote['saved_by']}")
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Quotes(bot))
