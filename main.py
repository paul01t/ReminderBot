import asyncio
from datetime import datetime, timezone
import discord
from discord.ext import commands
import json
import os
import logging
from dotenv import load_dotenv
from zoneinfo import ZoneInfo  # Python 3.9+

london_tz = ZoneInfo("Europe/London")
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
REMINDERS_FILE = "reminders.json"
reminderRole = "ReminderRole"

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True



class ReminderBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reminders = []
        self.load_reminders()

    def load_reminders(self):
        """Load reminders from JSON file"""
        if os.path.exists(REMINDERS_FILE):
            try:
                with open(REMINDERS_FILE, 'r') as f:
                    data = json.load(f)
                    self.reminders = data.get('reminders', [])
                print(f"Loaded {len(self.reminders)} reminders")
            except:
                print("Error loading reminders file")
                self.reminders = []
        else:
            self.reminders = []

    def save_reminders(self):
        """Save reminders to JSON file"""
        with open(REMINDERS_FILE, 'w') as f:
            json.dump({'reminders': self.reminders}, f, indent=2)

    async def check_reminders(self):
        """Background task to check and send reminders"""
        await self.wait_until_ready()

        while not self.is_closed():
            now = datetime.now(london_tz).timestamp()
            to_remove = []

            for reminder in self.reminders:
                if reminder['time'] <= now:
                    # Get channel and send reminder
                    channel = self.get_channel(reminder['channel_id'])
                    if channel:
                        guild = channel.guild
                        role = discord.utils.get(guild.roles, name=reminderRole)

                        if role:
                            await channel.send(f"⏰ {role.mention} **Reminder:** {reminder['text']}")
                        else:
                            await channel.send(f"⏰ **Reminder:** {reminder['text']}")

                    to_remove.append(reminder)

            # Remove sent reminders
            for reminder in to_remove:
                self.reminders.remove(reminder)

            if to_remove:
                self.save_reminders()

            await asyncio.sleep(30)  # Check every 30 seconds


# Create bot instance
bot = ReminderBot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(bot.check_reminders())

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "test" in message.content.lower():
        await message.channel.send("Test succesfull!")

    await bot.process_commands(message)

@bot.command()
@commands.has_role(reminderRole)
async def reminder(ctx):
    msg = ctx.message.content
    msg = msg.replace("!reminder ", "")

    parts = msg.split(' ', 1)
    if len(parts) < 2:
        await ctx.send("❌ Usage: `!reminder DD/MM/YYYY,HH:MM Reminder text`")
        return

    date_str = parts[0]
    reminder_text = parts[1]

    try:
        reminder_time = datetime.strptime(date_str, "%d/%m/%Y,%H:%M").replace(tzinfo=london_tz)
        now = datetime.now(london_tz)
        print(reminder_time)
        print(now)
        if reminder_time < now:
            await ctx.send("❌ That time is in the past!")
            return

        # Add reminder to list
        reminder_data = {
            'time': reminder_time.timestamp(),
            'text': reminder_text,
            'channel_id': ctx.channel.id,
            'guild_id': ctx.guild.id,
            'author_id': ctx.author.id
        }

        bot.reminders.append(reminder_data)
        bot.save_reminders()

        await ctx.send(f"✅ Reminder set for {reminder_time.strftime('%d/%m/%Y at %H:%M')}")

    except ValueError:
        await ctx.send("❌ Invalid date format. Use: `!reminder DD/MM/YYYY,HH:MM Reminder text`")


@bot.command()
async def listreminders(ctx):
    """List all pending reminders"""
    if not bot.reminders:
        await ctx.send("No pending reminders.")
        return

    reminder_list = "**Pending Reminders:**\n"
    for i, reminder in enumerate(bot.reminders, 1):
        dt = datetime.fromtimestamp(reminder['time'])
        reminder_list += f"{i}. {dt.strftime('%d/%m/%Y %H:%M')} - {reminder['text'][:50]}...\n"

    await ctx.send(reminder_list)


@bot.command()
async def clearreminders(ctx):
    """Clear all reminders (admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You need administrator permissions to use this command.")
        return

    bot.reminders = []
    bot.save_reminders()
    await ctx.send("✅ All reminders cleared.")


@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name=reminderRole)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send("✅ Roles assigned!")
    else:
        await ctx.send("❌ Roles missing!")

@bot.command()
async def remove(ctx):
    role = discord.utils.get(ctx.guild.roles, name=reminderRole)
    if role:
        await ctx.author.remove_roles(role)
        await ctx.send("✅ Roles removed!")
    else:
        await ctx.send("❌ Roles missing!")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
