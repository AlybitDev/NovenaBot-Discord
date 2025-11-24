import sqlite3
import uuid
import time
import discord
from discord.ext import commands, tasks
from typing import Optional
import json

conn = sqlite3.connect("workdir/novena-db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS novenas (
        novena_id TEXT PRIMARY KEY,
        novena_day INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        novena_name TEXT NOT NULL
)""")
conn.commit()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

with open('workdir/novenas.json', 'r') as file:
    novena_file = json.load(file)

@bot.event
async def on_ready():
    print(f"Signed in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synchronised.")
    background_task.start()
    print("Background task started")

@bot.tree.command(name="echo", description="Sends the given message back.")
async def echo(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)

@bot.tree.command(name="listnovenas", description="Gives all Novenas.")
async def listnovenas(interaction: discord.Interaction):
    await interaction.response.send_message("Novenas:\n- Mary Undoer of Knots")

@bot.tree.command(name="cancelnovena", description="Cancels the given Novena.")
async def cancelnovena(interaction: discord.Interaction, novena_id: Optional[str] = "none"):
    if novena_id == "none":
        await interaction.response.send_message("You need to give a valid Novena id. You can find all active Novenas that are available with /activenovenas.")
        return
    cursor.execute(
        """DELETE FROM novenas WHERE novena_id = ?""",
        (novena_id,)
    )
    if cursor.rowcount == 0:
        await interaction.response.send_message("An active Novena with this Novena id doesn't exist. You need to give a valid active Novena id.")
        return
    else:
        conn.commit()
        await interaction.response.send_message("Given Novena stopped succesfully.")

@bot.tree.command(name="newnovena", description="Starts a new Novena. See all Novenas with /listnovenas. Default of day is 1.")
async def newnovena(interaction: discord.Interaction, novena: Optional[str] = "none", day: Optional[int] = 1):
    if novena == "none":
        await interaction.response.send_message("You need to give a valid Novena. You can find all Novenas that are available with /listnovenas.")
        return
    try:
        test = novena_file[novena]
    except KeyError:
        await interaction.response.send_message("A Novena with this name doesn't exist. You can find all Novenas that are available with /listnovenas")
        return
    if day > 9 or day < 1:
        await interaction.response.send_message("You need to give a number between 1 and 9 as the day. »)
        return
    #if isinstance(interaction.message.channel, discord.DMChannel):
    cursor.execute(
        """INSERT INTO novenas (novena_id, novena_day, channel_id, timestamp, novena_name) VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), day, interaction.channel.id, time.time() - 86400, novena,)
    )
    conn.commit()
    await interaction.response.send_message("The Novena was succesfully added. The Novena will be started in an instant.")

@tasks.loop(seconds=5)  # task runs every 60 seconds
async def background_task():
    time_now_minus_86400 = time.time() - 86400
    cursor.execute(
        """SELECT novena_id FROM novenas WHERE timestamp < ?""",
        (time_now_minus_86400,)
    )
    ids = cursor.fetchall()
    for (novena_id,) in ids:
        cursor.execute(
            "SELECT channel_id, novena_day, novena_name FROM novenas WHERE novena_id = ?",
            (novena_id,)
        )
        channel_id, novena_day, novena_name = cursor.fetchone()
        channel = bot.get_channel(channel_id)
        if channel is None:
            channel = await bot.fetch_channel(channel_id)
        if novena_day < 9:
            await channel.send(novena_file[novena_name][str(novena_day)]+"\n\n> This is an automated message. If you want to cancel this Novena, send the command /cancelnovena with Novena id " + novena_id + " in the channel were this Novena was sent.")
            novena_day += 1
            cursor.execute(
                """UPDATE novenas SET novena_day=?, timestamp=? WHERE novena_id=?""",
                (novena_day,time.time(),novena_id,)
            )
            conn.commit()
        else:
            await channel.send(novena_file[novena_name][str(novena_day)] + "\n> This is an automated message.")
            cursor.execute(
                """DELETE FROM novenas WHERE novena_id = ?""",
                (novena_id,)
            )
            conn.commit()

bot.run("<discord-bot-secret-key>")
