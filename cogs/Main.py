# 導入Discord.py模組
import discord
# 導入commands指令模組
from discord.ext import commands
from discord import app_commands


from pytz import timezone
from datetime import datetime
from pytubefix import YouTube,Search
import ssl
ssl._create_default_https_context = ssl._create_stdlib_context

import torch
from TTS.api import TTS

import google.generativeai as genai
import os
import PIL.Image

import pathlib
import textwrap

import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

from config.config import Config

import speech_recognition as sr
import pandas as pd

from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.sinks import MP3Sink

import asyncio
import interactions

from discord.ext import listening
from typing import Literal, Optional
import os
import subprocess
import time

# global param
device = "cuda" if torch.cuda.is_available() else "cpu"
print(device)
gemini = {"gemini_model":"","gemini_chat":""}
tts_config = {"assistant":"","lang":"","speaker_wav":"","emotion":"","speed":0}
gemini_api_key = Config.gemini_api_key


genai.configure(api_key=gemini_api_key)
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
talk_allow_command = False  # talk_allow command visibility control

eastern = timezone('US/Eastern')

# path config
ffmpeg_path = "ffmpeg/ffmpeg-2024-09-09-git-9556379943-full_build/bin/ffmpeg.exe"
MusicBuffer_path = "MusicBuffer"
Music_path = "Music"
PodAudio_path = "PodAudio"

# test all path, if path not exist, return False and quit
def check_path(path):
    if os.path.exists(path):
        return True
    else:
        print(f"Path not found: {path}")
        return False

# setup: 啓動時刪除所有暫存器内MP3

if not check_path(ffmpeg_path) or not check_path(PodAudio_path):
    print("Path not found, please check the path.")
    exit()

if not check_path(MusicBuffer_path):
    os.makedirs(MusicBuffer_path)
    print(f"Path not found, create path: {MusicBuffer_path}")
if not check_path(Music_path):
    os.makedirs(Music_path)
    print(f"Path not found, create path: {Music_path}")

try:
    for ToDeleteMusic in os.listdir("MusicBuffer"):
        os.remove("MusicBuffer/"+str(ToDeleteMusic))
except Exception as e:
    print(f"Error deleting files: {e}")


#duration為指定錄製語音的時間，默認值為7秒
async def Voice_To_Text(duration=7): 
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("請開始説話:")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, phrase_time_limit=duration)
    try:
        Text = r.recognize_google(audio, language="en-GB")
    except sr.RequestError as e:
        Text = f"無法辨識{e}"
    except:
        Text = "無法辨識"

    return Text

# generate response voice
async def do_response_voice(user_query):
    response = gemini["gemini_chat"].send_message(user_query)
    response_text = str(response.text).replace("\n"," ").replace("*"," ")
    print(to_markdown(response.text))
    num = int(len(gemini["gemini_chat"].history)/2)
    try:
        tts.tts_to_file(text=response_text, speaker_wav=tts_config["speaker_wav"], language=tts_config["lang"],speed=tts_config["speed"],emotion=tts_config["emotion"], file_path=f'{MusicBuffer_path}/{tts_config["assistant"]}_{tts_config["lang"]}_gemini_{num}.wav')
    except Exception as ex:
        print(f"Error generating TTS: {ex}")
    return f'{MusicBuffer_path}/{tts_config["assistant"]}_{tts_config["lang"]}_gemini_{num}.wav'



# gemini output format function
def to_markdown(text):
    text = text.replace('•', '  *')
    text = textwrap.indent(text, '> ', predicate=lambda _: True)
    # return Markdown(text)  #use for notebook environment
    return text

def check_if_talk_command_should_be_visible(interaction: discord.Interaction):
    # This check ensures the command is shown only when the condition is True
    return talk_allow_command





async def is_in_guild(interaction: discord.Interaction):
    # If this interaction was invoked outside a guild
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used within a server.")
        return False
    return True

async def get_vc(interaction: discord.Interaction):
    # If the bot is currently in a vc
    if interaction.guild.voice_client is not None:
        # If the bot is in a vc other than the one of the user invoking the command
        if interaction.guild.voice_client.channel != interaction.user.voice.channel:
            # Move to the vc of the user invoking the command.
            await interaction.guild.voice_client.move_to(interaction.user.voice.channel)
        return interaction.guild.voice_client
    # If the user invoking the command is in a vc, connect to it
    if interaction.user.voice is not None:
        return await interaction.user.voice.channel.connect()



# 定義名為 Main 的 Cog
class Main(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.connections = {} 




    #%% 關鍵字觸發
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if self.bot.user.mentioned_in(message) and talk_allow_command:
            voice_state = message.author.voice
            
            if voice_state is None:
                error_msg = "Error: You are not in voice chat" if tts_config["lang"] == "en" else "Error: You are not in voice chat"
                await message.channel.send(error_msg)

            else:
                notify_msg = "Few minutes are needed to generate sound" if tts_config["lang"] == "en" else "Few minutes are needed to generate sound"
                notify_message = await message.channel.send(notify_msg)

                main_content = message.content.split(">")[-1] 
                username = message.author.name
                print("Username: ",username)
                print("Main content: ",main_content)
                voice_file = await do_response_voice(main_content)
                try:
                    vc = message.guild.voice_client
                    if vc is None:
                        vc = await voice_state.channel.connect()
                    elif vc.channel != voice_state.channel:
                        await vc.move_to(voice_state.channel)
                except Exception as ex:
                    print(ex)
                    return
                
                try:
                    notify_msg_edit = "Sound done. Ready to talk..." if tts_config["lang"] == "en" else "Sound done. Ready to talk..."
                    await notify_message.edit(content=notify_msg_edit)
                except Exception as ex:
                    print(f"Failed to edit the message: {ex}")
                    return

                try:
                    vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=voice_file))
                except Exception as ex:
                    print(f"Failed to play the audio: {ex}")
                    return
                
                # Wait until the sound finishes playing
                while vc.is_playing():
                    await asyncio.sleep(.1)

                try:
                    await notify_message.delete()
                except Exception as ex:
                    print(f"Failed to delete the message: {ex}")
                    return

                print("Successssss")
                return
            

        if message.content == "POD":
            await message.channel.send("POD コード:042 アシストの準備完了")

        # # Process other bot commands if needed
        # await bot.process_commands(message)


    @commands.Cog.listener()
    #only listen to voice get from local
    async def on_voice_state_update(self,member, before, after):
        if before.self_mute and not after.self_mute:
            print(f'{member} unmuted himself!')
            while True:
                Text =await Voice_To_Text(10)
                print(Text)
                if "robot" in Text and "come" in Text:
                    channel = member.voice.channel

                    if channel is None:
                        text_channel = discord.utils.get(member.guild.text_channels, name='jaiwei')
                        if text_channel:
                            await text_channel.send("You're not in a voice chat", ephemeral=True)
                    else:
                        voice_client = member.guild.voice_client
                        if voice_client:  
                            await voice_client.disconnect()
                        await channel.connect()
                        print(f"Connected to {channel}")
                        break

                if "robot" in Text and "left" in Text:
                    voice_client = member.guild.voice_client.channel
                    if voice_client:  
                        await voice_client.disconnect()
                        break

        if not before.self_mute and after.self_mute:
            print(f'{member} muted himself!')


        channel = discord.utils.get(member.guild.text_channels, name='jaiwei')  # Replace with your channel name
        if channel and before.self_mute and not after.self_mute:
            await channel.send(f'{member.mention} unmuted himself!')
        if channel and not before.self_mute and after.self_mute:
            await channel.send(f'{member.mention} muted himself!')

    # Global error handler for all app commands [Error: Maintainencing]
    # @commands.Cog.listener()
    # async def on_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
    #     if isinstance(error, app_commands.CheckFailure):
    #         await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    #     elif isinstance(error, app_commands.CommandInvokeError):
    #         await interaction.response.send_message("An unexpected error occurred while executing the command.", ephemeral=True)
    #     else:
    #         await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)




    

    #%% 前綴指令
    @app_commands.command(name= "pod",description="Call POD042")
    async def wake(self,interaction: discord.Interaction):
        channel = interaction.user.voice
        vc = await get_vc(interaction)
        if vc is None:
            await interaction.response.send_message("POD コード:042 アシストの準備完了")
        else:
            try:
                vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=f"{PodAudio_path}/ja/pod042_intro_ja_880_s05.wav"))
            except Exception as ex:
                await interaction.response.send_message(f"Error: {ex}")
                return


    @app_commands.command(name = "hello", description = "POD 042: Hello, world!")
    async def hello(self, interaction: discord.Interaction):
        # 回覆使用者的訊息
        await interaction.response.send_message("Hello, world!")

    @app_commands.command(name = "add", description = "POD 執行計算相加值")
    @app_commands.describe(a = "輸入數字", b = "輸入數字")
    async def add(self, interaction: discord.Interaction, a: int, b: int):
        await interaction.response.send_message(f"Total: {a + b}")

    @app_commands.command(name = "playmp3fromlocal", description = "POD 播放本端mp3")
    @app_commands.describe(music = "輸入音樂名稱")
    async def play_audio_local(self, interaction: discord.Interaction, music: str):
        time = datetime.now(eastern)
        channel = interaction.user.voice
        if channel is None:
            await interaction.response.send_message("You're not in a voice chat", ephemeral=True)
        else:

            vc = await get_vc(interaction)
            channel = channel.channel.name
            try:
                # Check if the file exists before trying to play it
                if not os.path.exists(f"{Music_path}/{music}.mp3"):
                    await interaction.response.send_message("Music not Found!!!", ephemeral=True)
                    return
            except Exception as ex:
                await interaction.response.send_message(f"Error: {ex}")
                return
            vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=f"{Music_path}/{music}.mp3"))
            await interaction.response.send_message(f"Music Playing: {music}", ephemeral=True)
            # Sleep while audio is playing.
            while vc.is_playing():
                time.sleep(.1)
            await vc.disconnect()


    @app_commands.command(name = "playmp3fromyoutube", description = "POD 播放YoutubeMP3")
    @app_commands.describe(music = "輸入音樂名稱",save = "要離綫下載保存嗎？")
    @app_commands.choices(save=[discord.app_commands.Choice(name="Yes" , value = 1),
                                discord.app_commands.Choice(name="No", value = 2)])
    async def play_audio_youTube(self, interaction: discord.Interaction, music: str, save:discord.app_commands.Choice[int]):
        # search music from Youtube and download
        results = Search(music)   
        for i in range(0,len(results.videos)):
            print(f"{i+1}: {results.videos[i]}")

        if save.value == 2:
            music_filepath = MusicBuffer_path
        else:
            music_filepath = Music_path

        if not results.videos:
            await interaction.response.send_message("Music not Found!!!", ephemeral=True)
            return
        yt = results.videos[0]
        title = yt.title
        # Send an initial response and store the message object for updates
        await interaction.response.defer(ephemeral=True)
        status_message = await interaction.followup.send(f"🎵 Downloading **{title}**... 0%")

        def progress_callback(stream,chunk,bytes_remaining):
            """ Updates the message with download progress """
            total_size = stream.filesize
            precent_complete = (total_size - bytes_remaining) / total_size * 100
            asyncio.run_coroutine_threadsafe(
                status_message.edit(content=f"🎵 Downloading **{title}**... {precent_complete:.2f}%"),
                asyncio.get_event_loop()
            )
        def complete_callback(stream, file_handle):
            """ Updates the message when the download is complete """
            asyncio.run_coroutine_threadsafe(
                status_message.edit(content=f"✅ **{title}** downloaded successfully!"),
                asyncio.get_event_loop()
            )
        
        # Attach progress tracking
        yt.register_on_progress_callback(progress_callback)
        yt.register_on_complete_callback(complete_callback)

        testname = "music1"
        yt.streams.filter().get_audio_only().download(output_path=music_filepath, filename=f'{testname}.mp3')

        channel = interaction.user.voice
        time = datetime.now(eastern)
        if channel is None:
            await status_message.edit(content="You're not in a voice chat")
        else:
            vc = await get_vc(interaction)
            channel = channel.channel.name
            try:
                vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=music_filepath+f"/{testname}.mp3"))
            except Exception as ex:
                await status_message.edit(content=f"Error: {ex}")
                return
            await status_message.edit(content=f"Music Playing: {title}")
            # Sleep while audio is playing.
            while vc.is_playing():
                await asyncio.sleep(0.1)

            if save.value == 2 and os.path.exists(music_filepath): 
                os.remove(music_filepath+f"/{music}.mp3")
                print("Music deleted successfully.")
            else: 
                print("Music not found.")




    @app_commands.command(name="starttalkingwith", description="I will talk to you")
    @app_commands.describe(name="選擇對象", language="語言")
    @app_commands.choices(
        name=[
            app_commands.Choice(name="pod042", value=1),
            app_commands.Choice(name="6O", value=2)
        ],
        language=[
            app_commands.Choice(name="en", value="en"),
            app_commands.Choice(name="ja", value="ja")
        ]
    )
    # @app_commands.check(check_if_talk_command_should_be_visible)
    async def start_talking(self, interaction: discord.Interaction, name: discord.app_commands.Choice[int], language:discord.app_commands.Choice[str]):
        assistant = name.name
        lang = language.name

        # tts voice parameter setup
        tts_config["assistant"] = assistant
        tts_config["lang"] = lang
        tts_config["speaker_wav"] = f"{PodAudio_path}/{lang}/{assistant}_{lang}_allsound.wav"
        tts_config["emotion"] = "Happy" if assistant == "6O" else "Neutral"
        tts_config["speed"] = 0.8 if assistant == "6O" else 1.0


        # gemini
        gemini["gemini_model"]=genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction="You are a tactical support unit 'pod042' , which act like the real pod042 in Nier:Automata. 'pod042' has a robotic, observant, and stoic personality. 'pod042' is highly knowledgeable about science, strategy and other related fields—expressing its thoughts and proposals using a logical and tactical mindset. However, this causes it to be unable to comprehend emotions or the feelings of others, therefore occasionally providing unhelpful or obvious answers. Pod 042 is loyal to you, willing to conduct whatever actions you commands despite observing how illogical they may be.",
            generation_config=genai.types.GenerationConfig(
            # Only one candidate for now.
            candidate_count=1,
            # stop_sequences=["x"],
            # max_output_tokens=20,
            temperature=1.5,
            ),
            )
        
        # 构建互动式聊天
        gemini["gemini_chat"] = gemini["gemini_model"].start_chat(
            history=[
                {"role": "user", "parts": "Pod"},
                {"role": "model", "parts": "This is tactical support unit pod042 assigned to user"},
            ]
        )
        global talk_allow_command
        talk_allow_command = True
        await interaction.response.send_message(f"{assistant} is ready to talk.", ephemeral=True)  


# Cog 載入 Bot 中
async def setup(bot: commands.Bot):

    await bot.add_cog(Main(bot))



