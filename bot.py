import os 
import asyncio
import discord
from discord.ext import commands
from discord.utils import get
from discord.ext import listening
from cogs.config.config import Config

from dotenv import load_dotenv
# pool that will be used for processing audio
# 1 signifies having 1 process in the pool
process_pool = listening.AudioProcessPool(1)

intents = discord.Intents.all()
intents.voice_states = True
bot = commands.Bot(command_prefix = ">", intents = intents)


# 當機器人完成啟動時
@bot.event
async def on_ready():
    slash = await bot.tree.sync()
    bot_command_num = len(bot.commands)
    
    print(f"目前登入身份 --> {bot.user}")
    print(f"載入 {len(slash)} 個斜線指令")
    print(f"載入 {bot_command_num} 個bot指令")
    # print(f"Synced {len(RecorderSynced)} commands to the guild.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="time"), status='online')

# 載入指令程式檔案
@bot.command()
async def load(ctx,extension):
    await bot.load_extension(f"cogs.{extension}")
    await ctx.send(f"Loaded {extension} done.")

# 卸載指令檔案
@bot.command()
async def unload(ctx, extension):
    await bot.unload_extension(f"cogs.{extension}")
    await ctx.send(f"UnLoaded {extension} done.")

# 重新載入程式檔案
@bot.command()
async def reload(ctx, extension):
    await bot.reload_extension(f"cogs.{extension}")
    await ctx.send(f"ReLoaded {extension} done.")


# Join voice channel
@bot.command()
async def join(ctx):
    channel_name = "聊天室"
    channel = get(ctx.guild.voice_channels, name=channel_name)
    
    if channel is not None:
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect() 
        try:
            await channel.connect()
            await ctx.send(f"Joined voice channel: {channel.name}")
        except discord.DiscordException as e:
            await ctx.send(f"Failed to join the voice channel: {str(e)}")
    else:
        await ctx.send(f"Voice channel '{channel_name}' not found.")
    
# Leave voice channel
@bot.command()
async def leave(ctx):
    voice_client = ctx.guild.voice_client
    await voice_client.disconnect()
    await ctx.send(f"Left voice channel: {voice_client.channel.name}")

# greetings~ (ctx.author chechk)
@bot.command()
async def greet(ctx):
    await ctx.send(f"Hello, {ctx.author.name}!")

#%%

# 一開始bot開機需載入全部程式檔案
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(Config.token)

# 確定執行此py檔才會執行

if __name__ == "__main__":
    load_dotenv()
    try:
        asyncio.run(main())
    finally:
        # good practice
        process_pool.cleanup_processes()
    