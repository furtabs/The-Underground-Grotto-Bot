import discord
from discord.ext import commands, tasks
import json
import json5
import os
from datetime import datetime, timedelta
import asyncio
import pytz

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

# Load or initialize database data
def load_db():
    if not os.path.exists(DB_FILE):
        return {"quotes": [], "birthdays": {}, "levels": {}}
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load birthday data from unified database
def load_birthdays():
    data = load_db()
    return data.get('birthdays', {})

def save_birthdays(birthday_data):
    data = load_db()
    data['birthdays'] = birthday_data
    save_db(data)

# Initialize birthday data
birthday_data = load_birthdays()

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()  # Start the birthday check task

    @commands.slash_command()
    async def set_birthday(self, ctx):
        """Set your birthday using a dropdown for month and input for day."""
        # Create month options
        month_options = [discord.SelectOption(label=month, value=str(index + 1)) for index, month in enumerate([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])]

        # Create dropdown for month
        month_select = discord.ui.Select(placeholder="Select your birth month", options=month_options)

        # Create a view to hold the month dropdown
        view = discord.ui.View()
        view.add_item(month_select)

        # Send the month dropdown to the channel
        await ctx.respond("Please select your birth month:", view=view)

        # Wait for the user to select a month
        def check_month(interaction):
            return interaction.user == ctx.author and interaction.data['component_type'] == 3  # 3 is the type for Select

        try:
            month_interaction = await self.bot.wait_for("interaction", check=check_month, timeout=60.0)
            month = int(month_select.values[0])  # Get the selected month

            # Acknowledge the month selection
            await month_interaction.response.send_message(f"You selected: {month_options[month - 1].label}. Please type your birth day (1-31):", ephemeral=True)

            # Wait for the user to respond with the day in the channel
            def check_day(message):
                return message.author == ctx.author and message.channel == ctx.channel

            day_message = await self.bot.wait_for("message", check=check_day, timeout=60.0)
            day = day_message.content.strip()

            # Validate the day input
            if not day.isdigit() or not (1 <= int(day) <= 31):
                await ctx.channel.send(f"{ctx.author.mention}, please enter a valid day between 1 and 31.")
                return

            # Format the birthday as YYYY-MM-DD
            birthday = f"2023-{month:02}-{int(day):02}"  # Using a fixed year for simplicity

            # Extract month name for the response
            month_name = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"][month - 1]
            formatted_birthday = f"{month_name} {int(day)}"

            user_id = str(ctx.author.id)
            birthday_data[user_id] = birthday
            save_birthdays(birthday_data)

            # Send the confirmation message in the channel
            await ctx.channel.send(f"🎉 {ctx.author.mention}, your birthday has been set to {formatted_birthday}!")

        except Exception as e:
            # Handle the error gracefully
            if isinstance(e, discord.errors.NotFound):
                await ctx.channel.send(f"{ctx.author.mention}, an error occurred while processing your request. Please try again.")
            else:
                await ctx.channel.send(f"{ctx.author.mention}, you took too long to respond or an error occurred.")

    @tasks.loop(hours=24)  # Check every 24 hours
    async def check_birthdays(self):
        # Get the current time in EST
        est = pytz.timezone('America/New_York')
        now = datetime.now(est)

        # Check if it's 12 AM
        if now.hour == 0 and now.minute == 0:
            today = now.strftime("%Y-%m-%d")
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            birthday_role_id = get_setting('birthday_role_id')
            
            # Check for users whose birthday is today
            for user_id, birthday in birthday_data.items():
                if birthday == today:
                    user = self.bot.get_user(int(user_id))
                    if user:
                        # Send birthday message
                        channel_id = get_setting('birthday_channel_id')
                        if channel_id:
                            channel = self.bot.get_channel(int(channel_id))
                            if channel:
                                await channel.send(f"🎉 Happy Birthday {user.mention}! 🎉")
                        
                        # Give birthday role if configured
                        if birthday_role_id:
                            # Try to find the user in any guild the bot is in
                            for guild in self.bot.guilds:
                                member = guild.get_member(int(user_id))
                                if member:
                                    birthday_role = guild.get_role(int(birthday_role_id))
                                    if birthday_role and birthday_role not in member.roles:
                                        try:
                                            await member.add_roles(birthday_role)
                                            # Send confirmation to the birthday channel
                                            if channel_id:
                                                channel = self.bot.get_channel(int(channel_id))
                                                if channel:
                                                    await channel.send(f"🎁 {user.mention} has been given the birthday role!")
                                        except discord.Forbidden:
                                            # Bot doesn't have permission to manage roles
                                            pass
                                        except Exception as e:
                                            print(f"Error assigning birthday role: {e}")
                                    break  # Found the user, no need to check other guilds
            
            # Check for users whose birthday was yesterday and remove the role
            if birthday_role_id:
                for user_id, birthday in birthday_data.items():
                    if birthday == yesterday:
                        # Try to find the user in any guild the bot is in
                        for guild in self.bot.guilds:
                            member = guild.get_member(int(user_id))
                            if member:
                                birthday_role = guild.get_role(int(birthday_role_id))
                                if birthday_role and birthday_role in member.roles:
                                    try:
                                        await member.remove_roles(birthday_role)
                                        # Send notification to the birthday channel
                                        channel_id = get_setting('birthday_channel_id')
                                        if channel_id:
                                            channel = self.bot.get_channel(int(channel_id))
                                            if channel:
                                                await channel.send(f"👋 Birthday role removed from {member.mention}. See you next year!")
                                    except discord.Forbidden:
                                        # Bot doesn't have permission to manage roles
                                        pass
                                    except Exception as e:
                                        print(f"Error removing birthday role: {e}")
                                break  # Found the user, no need to check other guilds
        else:
            await asyncio.sleep(60)

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()