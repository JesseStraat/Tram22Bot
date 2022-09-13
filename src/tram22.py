import requests
import json
import disnake
from disnake.ext import commands, tasks
from dotenv import load_dotenv
import os
import tweepy
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import asyncio
import datetime
import pytz


# Setup and input
if not os.path.exists('../env/.env'):
    os.makedirs(os.path.dirname('../env/.env'), exist_ok=True)
    with open('../env/.env', 'w') as env:
        envstr = '# .env'
        print("Enter your bot's token:")
        envtoken = input()
        envstr += '\nTOKEN = ' + envtoken
        
        env.write(envstr)
        print('.env created!')

for jsonfile in ['tram22.json', 'telegramdata.json', 'discorddata.json', 'discordguilddata.json']:
    if not os.path.exists('../json/'+jsonfile):
        os.makedirs(os.path.dirname('../json/'+jsonfile), exist_ok=True)
        with open('../json/'+jsonfile, 'w') as jsonname:
            json.dump({}, jsonname, indent = 4)
        print(jsonfile+' created!')

print('Starting bot...')

# .env
load_dotenv('../env/.env')

# Set up logging
logging.basicConfig()

# Setting up data url
url = 'https://www.u-ov.info/api/website/graphql'

# Discord stuff
TOKEN = os.getenv('DISCORDTOKEN')
intents = disnake.Intents.default()
client = commands.InteractionBot(intents=intents)#, testguilds = [850044087428317184])

# Twitter stuff
BEARER = os.getenv('BEARER')
CONSUMERKEY = os.getenv('CONSUMERKEY')
CONSUMERSECRET = os.getenv('CONSUMERSECRET')
ACCESSTOKEN = os.getenv('ACCESSTOKEN')
ACCESSTOKENSECRET = os.getenv('ACCESSTOKENSECRET')
twclient = tweepy.Client(BEARER, CONSUMERKEY, CONSUMERSECRET, ACCESSTOKEN, ACCESSTOKENSECRET)

# Telegram stuff
TTOKEN = os.getenv('TELEGRAMTOKEN')
application = ApplicationBuilder().token(TTOKEN).build()

def timeconvert(time: str):
    try:
        return str(datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=pytz.timezone('Europe/Amsterdam')))[:-6]
    except:
    	try:
            return str(datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=pytz.timezone('Europe/Amsterdam')))[:-6]
    	except:
    	    return str(datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).astimezone(tz=pytz.timezone('Europe/Amsterdam')))[:-6]

def autotweet(textlist: list):
    tweets, current = [], ""
    for line in textlist:
        if len(current) + 2 + len(line) > 280:
            if current != "":
                tweets.append(current)
            current = ""
            
            # Test line is too large for a single tweet: split into smaller parts
            if len(line) > 280:
                # This is a comparable process to the larger text splitting
                words = line.split()
                for word in words:
                    if len(current) + 1 + len(word) > 280:
                        tweets.append(current)
                        current = word
                    else:
                        current += " " + word
                tweets.append(current)
                current = ""
            
            else:
                current = line
        else:
            current += "\n" + line
    tweets.append(current)
   
    lasttweet = twclient.create_tweet(text=tweets[0])
    tweetid = lasttweet.data['id']
    for tweet in tweets[1:]:
        lasttweettemp = lasttweet
        lasttweet = twclient.create_tweet(text = tweet, in_reply_to_tweet_id = lasttweettemp.data['id'])
    return tweetid

async def getDisruptions():
    # Find how many disruptions there are currently
    npayload = {"query":"query DisruptionWidgetQuery(\n  $website: String!\n) {\n  website(id: $website) {\n    disruptionAmounts {\n      amount\n      type\n    }\n  }\n}\n",
                "variables":{"website":"U_OV"}}
    
    ndisruptions = 0
    for distype in json.loads(requests.post(url, json = npayload).text)['data']['website']['disruptionAmounts']:
        ndisruptions += distype['amount']
    
    # Find out what the disruptions are
    payload = {"query":"query DisruptionOverviewQuery(\n  $website: String!\n  $count: Int\n  $cursor: String\n  $query: String\n) {\n  website(id: $website) {\n    ...DisruptionList\n  }\n}\n\nfragment DisruptionItem_item on GQDisruption {\n  advice\n  cause\n  createdAt\n  disruptionId\n  effect\n  extraInformation\n  status\n  id\n  measure\n  name\n  quays {\n    quay {\n      stopplace {\n        name\n        id\n        uri\n        place {\n          town\n          name\n        }\n      }\n    }\n  }\n  routeDirections {\n    routeDirection {\n      dataOwner\n      destination\n      direction\n      internalId\n    }\n    route {\n      publicLineNr\n    }\n  }\n  type\n  updatedAt\n  validFrom\n  validTo\n  website\n}\n\nfragment DisruptionList on GQWebsite {\n  qry: disruptions(query: $query) {\n    items: disruptions(first: $count, after: $cursor) {\n      edges {\n        node {\n          ...DisruptionItem_item\n          __typename\n        }\n        cursor\n      }\n      pageInfo {\n        hasNextPage\n        endCursor\n      }\n    }\n  }\n}\n",
               "variables":{
                               "website":"U_OV",
                               "count":ndisruptions,
                               "cursor":None,
                               "query":""
                           }
               }
    
    info = json.loads(requests.post(url, json = payload).text)['data']['website']['qry']['items']['edges']
    
    # Current disruption database
    with open('../json/tram22.json', 'r') as tram22json:
        database = json.load(tram22json)
    
    # Checking if disruptions have ended
    poplist = []
    for disruption in database:
        exists = False
        for disr in info:
            if disruption == disr['cursor']:
                exists = True
        if not exists:
            poplist.append(disruption)
            messString = f"Storing {disruption} is opgelost."
            
            # Tweet end disruption
            try:
                twclient.create_tweet(text=timeconvert(requests.get('http://just-the-time.appspot.com/').content.decode('utf-8')) +" \n" + messString, quote_tweet_id=database[disruption]['tweetid'])
            except Exception as e:
                print('Quote retweet failed.')
                print(e)
            
            try:
                twclient.create_tweet(text=timeconvert(requests.get('http://just-the-time.appspot.com/').content.decode('utf-8')) +" \n" + messString, in_reply_to_tweet_id=database[disruption]['tweetid'])
            except Exception as e:
                print('Reply tweet failed.')
                print(e)
            
            # Send Discord message
            try:
                with open('../json/discorddata.json', 'r') as discorddatajson:
                    discorddata = json.load(discorddatajson)
                
                for user in discorddata:
                    try:
                        dm = await client.fetch_user(user)
                        await dm.send(messString)
                    except Exception as e:
                        print(f'Discord message failed, user: {user}.')
                        print(e)
            except Exception as e:
                print('Discord direct message failed.')
                print(e)
            
            try:
                with open('../json/discordguilddata.json', 'r') as discordguilddatajson:
                    discordguilddata = json.load(discordguilddatajson)
                
                for guild in discordguilddata:
                    for channel in discordguilddata[guild]:
                        try:
                            chan = await client.fetch_channel(channel)
                            await chan.send(messString)
                        except Exception as e:
                            print(f'Discord message failed, channel: {channel}.')
                            print(e)
            except Exception as e:
                print('Discord guild message failed.')
                print(e)
            
            # Send Telegram message
            try:
                with open('../json/telegramdata.json', 'r') as telegramdatajson:
                    telegramdata = json.load(telegramdatajson)
                for chatid in telegramdata:
                    try:
                        requests.post(f'https://api.telegram.org/bot{TTOKEN}/sendMessage?chat_id={chatid}&text={messString}')
                    except Exception as e:
                        print(f'Telegran message failed, user: {user}.')
                        print(e)
            except Exception as e:
                print('Telegram message failed.')
                print(e)
    
    for popper in poplist:
        database.pop(popper)
    
    # Finding new disruptions for line 22
    for disruption in info:
        for lijn in disruption['node']['routeDirections']:
            try:
                if lijn['route']['publicLineNr'] == '22':
                    # Do something if this is line 22
                    if disruption['cursor'] not in database:
                        database[disruption['cursor']] = disruption['node']
                        
                        # Create string
                        messageList = [f"Tram 22 update (storing {disruption['cursor']}):", f"{disruption['node']['effect']}", f"Oorzaak: {disruption['node']['cause']}", f"Advies: {disruption['node']['advice']}", f"Verwachte duur: {timeconvert(disruption['node']['validFrom'])} - {timeconvert(disruption['node']['validTo'])}"]
                        message = "\n".join(messageList)
                        
                        # Tweet new disruption
                        try:
                            tweetid = autotweet([timeconvert(requests.get('http://just-the-time.appspot.com/').content.decode('utf-8'))] + messageList)
                            database[disruption['cursor']]['tweetid'] = tweetid
                        except Exception as e:
                            print('Tweet failed.')
                            print(e)
                        
                        # Send Discord message
                        try:
                            with open('../json/discorddata.json', 'r') as discorddatajson:
                                discorddata = json.load(discorddatajson)
                            for user in discorddata:
                                try:
                                    dm = await client.fetch_user(user)
                                    await dm.send(message)
                                except:
                                    pass
                        except Exception as e:
                            print('Discord message failed.')
                            print(e)
                        
                        # Send Telegram message
                        try:
                            with open('../json/telegramdata.json', 'r') as telegramdatajson:
                                telegramdata = json.load(open('../json/telegramdata.json', 'r'))
                            for chatid in telegramdata:
                                requests.post(f'https://api.telegram.org/bot{TTOKEN}/sendMessage?chat_id={chatid}&text={message}')
                        except Exception as e:
                            print('Telegram message failed.')
                            print(e)
            except:
                pass
    with open('../json/tram22.json', 'w') as tram22json:
        json.dump(database, tram22json, indent = 4)

@client.event
async def on_ready():
    print("I'm ready!")
    if not disruptionLoop.is_running():
        disruptionLoop.start()

@tasks.loop(minutes = 1.0)
async def disruptionLoop():
    await getDisruptions()

# Discord commands
@client.slash_command(description = "Voegt je toe aan of verwijdert je van de Tram 22 message list.")
async def subscribe(inter):
    with open('../json/discorddata.json', 'r') as discorddatajson:
        discorddata = json.load(discorddatajson)
    if inter.author.id not in discorddata:
        discorddata.append(inter.author.id)
        dm = await inter.author.create_dm()
        await inter.response.send_message(f"Hey {inter.author}! Ik heb je toegevoegd aan de message list! Ik heb je als test een DM gestuurd. Als je deze niet ontvangen hebt, staan je DMs niet open voor mij!", ephemeral=True)
        await dm.send(f"Hey, {inter.author}! Ik heb je toegevoegd aan de message list! Je hebt je DMs goed ingesteld om mijn berichten te ontvangen!")
    else:
        discorddata.pop(discorddata.index(inter.author.id))
        await inter.response.send_message(f"Hey {inter.author}! Ik heb je verwijderd uit de message list!", ephemeral=True)
    with open('../json/discorddata.json', 'w') as discorddatajson:
        json.dump(discorddata, discorddatajson, indent = 4)

@client.slash_command(description = "Voegt dit kanaal toe aan of verwijdert het van de Tram 22 message list.")
@commands.has_permissions(manage_channels = True)
async def subscribechannel(inter):
    with open('../json/discordguilddata.json', 'r') as discordguilddatajson:
        discordguilddata = json.load(discordguilddatajson)
    if str(inter.guild_id) not in discordguilddata:
        discordguilddata[str(inter.guild_id)] = []
    if inter.channel_id not in discordguilddata[str(inter.guild_id)]:
        discordguilddata[str(inter.guild_id)].append(inter.channel_id)
        await inter.response.send_message(f"Hey! Ik heb dit kanaal toegevoegd aan de message list!")
    else:
        discordguilddata[str(inter.guild_id)].pop(discordguilddata[str(inter.guild_id)].index(inter.channel_id))
        await inter.response.send_message(f"Hey! Ik heb dit kanaal verwijderd uit de message list!")
    with open('../json/discordguilddata.json', 'w') as discordguilddatajson:
        json.dump(discordguilddata, discordguilddatajson, indent = 4)

@client.slash_command(description = "Stuurt een invite link voor deze bot.")
async def invite(inter):
    await inter.response.send_message("https://discord.com/api/oauth2/authorize?client_id=1007389215245475922&permissions=277025459200&scope=bot%20applications.commands", ephemeral=True)

@client.event
async def on_guild_remove(guild):
    with open('../json/discordguilddata.json', 'r') as discordguilddatajson:
        discordguilddata = json.load(discordguilddatajson)
    
    try:
        discordguilddata.pop(str(guild.id))
    except:
        pass
    
    with open('../json/discordguilddata.json', 'w') as discordguilddatajson:
        json.dump(discordguilddata, discordguilddatajson, indent = 4)
        

# Telegram commands

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welkom bij Tram22Bot. Gebruik /subscribe om je in te schrijven voor onze message list.")

async def telsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open('../json/telegramdata.json', 'r') as telegramdatajson:
        telegramdata = json.load(telegramdatajson)
    if update.message.chat_id not in telegramdata:
        telegramdata.append(update.message.chat_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ik heb je toegevoegd aan de message list!")
    else:
        telegramdata.pop(telegramdata.index(update.message.chat_id))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ik heb je verwijderd uit de message list!")
        #await inter.response.send_message(f"Hey {inter.author}! Ik heb je verwijderd uit de message list!", ephemeral=True)
    with open('../json/telegramdata.json', 'w') as telegramdatajson:
        json.dump(telegramdata, telegramdatajson, indent = 4)

# Running the Telegram bot

start_handler = CommandHandler('start', start)
application.add_handler(start_handler)
sub_handler = CommandHandler('subscribe', telsubscribe)
application.add_handler(sub_handler)

# Combining Telegram and Discord into a single loop

loop = asyncio.get_event_loop()
loop.create_task(client.start(TOKEN))
loop.create_task(application.run_polling())
loop.run_forever()