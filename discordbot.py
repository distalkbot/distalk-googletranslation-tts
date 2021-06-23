import asyncio
import discord
from discord.ext import commands
import os
import traceback
import urllib.parse
import re

prefix = os.getenv('DISCORD_BOT_PREFIX', default='🦑')
lang = os.getenv('DISCORD_BOT_LANG', default='ja')
token = os.environ['DISCORD_BOT_TOKEN']
client = commands.Bot(command_prefix=prefix)

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name=f'{prefix}ヘルプ | 0/{len(client.guilds)}サーバー'))

@client.command()
async def 接続(ctx):
    if ctx.message.guild:
        if ctx.author.voice is None:
            await ctx.send('ボイスチャンネルに接続してから呼び出してください。')
        else:
            if ctx.guild.voice_client:
                if ctx.author.voice.channel == ctx.guild.voice_client.channel:
                    await ctx.send('接続済みです。')
                else:
                    await ctx.voice_client.disconnect()
                    await asyncio.sleep(0.5)
                    await ctx.author.voice.channel.connect()
            else:
                await ctx.author.voice.channel.connect()

@client.command()
async def 切断(ctx):
    if ctx.message.guild:
        if ctx.voice_client is None:
            await ctx.send('ボイスチャンネルに接続していません。')
        else:
            await ctx.voice_client.disconnect()

@client.event
async def on_message(message):
    if message.content.startswith(prefix):
        pass
    else:
        if message.guild.voice_client:
            text = message.content
            text = text.replace('\n', '、')
            pattern = r'^<@\d*>'
            if re.match(pattern, text):
                match = re.search(r'^<@(\d*)>', text)
                uid = match.group(1)
                user = await client.fetch_user(uid)
                username = user.name + '、'
                text = re.sub(pattern, username, text)
            pattern = r'https://tenor.com/view/[\w/:%#\$&\?\(\)~\.=\+\-]+'
            text = re.sub(pattern, '画像', text)
            pattern = r'https://[\w/:%#\$&\?\(\)~\.=\+\-]+(\.jpg|\.jpeg|\.gif|\.png|\.bmp)'
            text = re.sub(pattern, '、画像', text)
            pattern = r'https://[\w/:%#\$&\?\(\)~\.=\+\-]+'
            text = re.sub(pattern, '、URL', text)
            text = message.author.name + '、' + text
            if text[-1:] == 'w' or text[-1:] == 'W' or text[-1:] == 'ｗ' or text[-1:] == 'W':
                while text[-2:-1] == 'w' or text[-2:-1] == 'W' or text[-2:-1] == 'ｗ' or text[-2:-1] == 'W':
                    text = text[:-1]
                text = text[:-1] + '、ワラ'
            if message.attachments:
                text += '、添付ファイル'
            if len(text) < 100:
                s_quote = urllib.parse.quote(text)
                mp3url = 'http://translate.google.com/translate_tts?ie=UTF-8&q=' + s_quote + '&tl=' + lang + '&client=tw-ob'
                while message.guild.voice_client.is_playing():
                    await asyncio.sleep(0.5)
                message.guild.voice_client.play(discord.FFmpegPCMAudio(mp3url))
            else:
                await message.channel.send('100文字以上は読み上げできません。')
        else:
            pass
    await client.process_commands(message)

@client.event
async def on_voice_state_update(member, before, after):
    if before.channel is None:
        if member.id == client.user.id:
            await client.change_presence(activity=discord.Game(name=f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'))
        else:
            if member.guild.voice_client is None:
                await asyncio.sleep(0.5)
                await after.channel.connect()
            else:
                if member.guild.voice_client.channel is after.channel:
                    text = member.name + 'さんが入室しました'
                    s_quote = urllib.parse.quote(text)
                    mp3url = 'http://translate.google.com/translate_tts?ie=UTF-8&q=' + s_quote + '&tl=' + lang + '&client=tw-ob'
                    while member.guild.voice_client.is_playing():
                        await asyncio.sleep(0.5)
                    member.guild.voice_client.play(discord.FFmpegPCMAudio(mp3url))
    elif after.channel is None:
        if member.id == client.user.id:
            await client.change_presence(activity=discord.Game(name=f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'))
        else:
            if member.guild.voice_client.channel is before.channel:
                if len(member.guild.voice_client.channel.members) == 1:
                    await asyncio.sleep(0.5)
                    await member.guild.voice_client.disconnect()
                else:
                    text = member.name + 'さんが退室しました'
                    s_quote = urllib.parse.quote(text)
                    mp3url = 'http://translate.google.com/translate_tts?ie=UTF-8&q=' + s_quote + '&tl=' + lang + '&client=tw-ob'
                    while member.guild.voice_client.is_playing():
                        await asyncio.sleep(0.5)
                    member.guild.voice_client.play(discord.FFmpegPCMAudio(mp3url))
    elif before.channel != after.channel:
        if member.guild.voice_client.channel is before.channel:
            if len(member.guild.voice_client.channel.members) == 1 or member.voice.self_mute:
                await asyncio.sleep(0.5)
                await member.guild.voice_client.disconnect()
                await asyncio.sleep(0.5)
                await after.channel.connect()

@client.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, 'original', error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    await ctx.send(error_msg)

@client.command()
async def ヘルプ(ctx):
    message = f'''◆◇◆{client.user.name}の使い方◆◇◆
{prefix}＋コマンドで命令できます。
{prefix}接続：ボイスチャンネルに接続します。
{prefix}切断：ボイスチャンネルから切断します。'''
    await ctx.send(message)

client.run(token)
