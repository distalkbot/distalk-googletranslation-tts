import asyncio
import discord
from discord import app_commands
import os
import traceback
import urllib.parse
import re
from emoji import unicode_codes
import json
import psycopg2

prefix = os.getenv('DISCORD_BOT_PREFIX', default='🦑')
lang = os.getenv('DISCORD_BOT_LANG', default='ja')
token = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
with open('emoji_ja.json', encoding='utf-8') as file:
    emoji_dataset = json.load(file)
database_url = os.environ.get('DATABASE_URL')

@client.event
async def on_ready():
    presence = f'{prefix}ヘルプ | 0/{len(client.guilds)}サーバー'
    await client.change_presence(activity=discord.Game(name=presence))
    await tree.sync()

@client.event
async def on_guild_join(guild):
    presence = f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'
    await client.change_presence(activity=discord.Game(name=presence))

@client.event
async def on_guild_remove(guild):
    presence = f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'
    await client.change_presence(activity=discord.Game(name=presence))

@tree.command(description="読み上げbotをボイスチャンネルに接続します")
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
                    await asyncio.sleep(1)
                    await ctx.author.voice.channel.connect()
            else:
                await ctx.author.voice.channel.connect()

@tree.command()
async def 切断(ctx):
    if ctx.message.guild:
        if ctx.voice_client is None:
            await ctx.send('ボイスチャンネルに接続していません。')
        else:
            await ctx.voice_client.disconnect()

@tree.command()
async def 辞書確認(ctx):
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            sql = 'SELECT * FROM dictionary WHERE guildId = %s'
            value = (ctx.guild.id, )
            cur.execute(sql, value)
            rows = cur.fetchall()
            text = '辞書一覧\n'
            if len(rows) == 0:
                text += 'なし'
            else:
                for row in rows:
                    text += f'{row[1]}→{row[2]}\n'
            await ctx.send(text)

@client.event
async def on_message(message):
    if message.guild.voice_client:
        if not message.author.bot:
            if not message.content.startswith(prefix):
                text = message.content

                # Add author's name
                text = message.author.name + '、' + text

                # Replace dictionary
                with psycopg2.connect(database_url) as conn:
                    with conn.cursor() as cur:
                        sql = 'SELECT * FROM dictionary WHERE guildId = %s'
                        value = (message.guild.id, )
                        cur.execute(sql, value)
                        rows = cur.fetchall()
                        for row in rows:
                            word = row[1]
                            kana = row[2]
                            text = text.replace(word, kana)

                # Replace new line
                text = text.replace('\n', '、')

                # Replace mention to user
                pattern = r'<@!?(\d+)>'
                match = re.findall(pattern, text)
                for user_id in match:
                    user = await client.fetch_user(user_id)
                    user_name = f'、{user.name}へのメンション、'
                    text = re.sub(rf'<@!?{user_id}>', user_name, text)

                # Replace mention to role
                pattern = r'<@&(\d+)>'
                match = re.findall(pattern, text)
                for role_id in match:
                    role = message.guild.get_role(int(role_id))
                    role_name = f'、{role.name}へのメンション、'
                    text = re.sub(f'<@&{role_id}>', role_name, text)

                # Replace Unicode emoji
                text = re.sub(r'[\U0000FE00-\U0000FE0F]', '', text)
                text = re.sub(r'[\U0001F3FB-\U0001F3FF]', '', text)
                for char in text:
                    if char in unicode_codes.EMOJI_DATA and char in emoji_dataset:
                        text = text.replace(char, emoji_dataset[char]['short_name'])

                # Replace Discord emoji
                pattern = r'<:([a-zA-Z0-9_]+):\d+>'
                match = re.findall(pattern, text)
                for emoji_name in match:
                    emoji_read_name = emoji_name.replace('_', ' ')
                    text = re.sub(rf'<:{emoji_name}:\d+>', f'、{emoji_read_name}、', text)

                # Replace URL
                pattern = r'https://tenor.com/view/[\w/:%#\$&\?\(\)~\.=\+\-]+'
                text = re.sub(pattern, '画像', text)
                pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+(\.jpg|\.jpeg|\.gif|\.png|\.bmp)'
                text = re.sub(pattern, '、画像', text)
                pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
                text = re.sub(pattern, '、URL', text)

                # Replace spoiler
                pattern = r'\|{2}.+?\|{2}'
                text = re.sub(pattern, '伏せ字', text)

                # Replace laughing expression
                if text[-1:] == 'w' or text[-1:] == 'W' or text[-1:] == 'ｗ' or text[-1:] == 'W':
                    while text[-2:-1] == 'w' or text[-2:-1] == 'W' or text[-2:-1] == 'ｗ' or text[-2:-1] == 'W':
                        text = text[:-1]
                    text = text[:-1] + '、ワラ'

                # Add attachment presence
                for attachment in message.attachments:
                    if attachment.filename.endswith((".jpg", ".jpeg", ".gif", ".png", ".bmp")):
                        text += '、画像'
                    else:
                        text += '、添付ファイル'

                if len(text) < 100:
                    s_quote = urllib.parse.quote(text)
                    mp3url = f'http://translate.google.com/translate_tts?ie=UTF-8&q={s_quote}&tl={lang}&client=tw-ob'
                    while message.guild.voice_client.is_playing():
                        await asyncio.sleep(1)
                    source = await discord.FFmpegOpusAudio.from_probe(mp3url)
                    message.guild.voice_client.play(source)
                else:
                    await message.channel.send('100文字以上は読み上げできません。')
    await app_commands(message)

@client.event
async def on_voice_state_update(member, before, after):
    if before.channel is None:
        if member.id == client.user.id:
            presence = f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'
            await client.change_presence(activity=discord.Game(name=presence))
        else:
            if member.guild.voice_client is None:
                await asyncio.sleep(1)
                await after.channel.connect()
            else:
                if member.guild.voice_client.channel is after.channel:
                    text = member.name + 'さんが入室しました'
                    s_quote = urllib.parse.quote(text)
                    mp3url = f'http://translate.google.com/translate_tts?ie=UTF-8&q={s_quote}&tl={lang}&client=tw-ob'
                    while member.guild.voice_client.is_playing():
                        await asyncio.sleep(1)
                    source = await discord.FFmpegOpusAudio.from_probe(mp3url)
                    member.guild.voice_client.play(source)
    elif after.channel is None:
        if member.id == client.user.id:
            presence = f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'
            await client.change_presence(activity=discord.Game(name=presence))
        else:
            if member.guild.voice_client:
                if member.guild.voice_client.channel is before.channel:
                    if len(member.guild.voice_client.channel.members) == 1:
                        await asyncio.sleep(1)
                        await member.guild.voice_client.disconnect()
                    else:
                        text = member.name + 'さんが退室しました'
                        s_quote = urllib.parse.quote(text)
                        mp3url = f'http://translate.google.com/translate_tts?ie=UTF-8&q={s_quote}&tl={lang}&client=tw-ob'
                        while member.guild.voice_client.is_playing():
                            await asyncio.sleep(1)
                        source = await discord.FFmpegOpusAudio.from_probe(mp3url)
                        member.guild.voice_client.play(source)
    elif before.channel != after.channel:
        if member.guild.voice_client:
            if member.guild.voice_client.channel is before.channel:
                if len(member.guild.voice_client.channel.members) == 1 or member.voice.self_mute:
                    await asyncio.sleep(1)
                    await member.guild.voice_client.disconnect()
                    await asyncio.sleep(1)
                    await after.channel.connect()

@client.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, 'original', error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    await ctx.send(error_msg)

@tree.command()
async def ヘルプ(ctx):
    message = f'''◆◇◆{client.user.name}の使い方◆◇◆
{prefix}接続：ボイスチャンネルに接続します。
{prefix}切断：ボイスチャンネルから切断します。
{prefix}辞書確認：辞書に登録されている単語を確認します。
{prefix}辞書追加 単語 よみがな：辞書に[単語]を[よみがな]として追加します。
{prefix}辞書削除 単語：辞書から[単語]のよみがなを削除します。'''
    await ctx.send(message)

client.run(token)
