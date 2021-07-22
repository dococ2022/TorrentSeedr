import requests
from time import time
import base64, asyncio

from src.objs import *
from src.functions.bars import progressBar
from src.functions.floodControl import floodControl
from src.functions.convert import convertSize, convertTime
from src.functions.exceptions import exceptions, noAccount

#: Add torrent into the user's account
async def addTorrent(message, userLanguage, magnetLink=None, messageId=None):
    userId = message.from_user.id

    if floodControl(message, userLanguage):
        ac = dbSql.getDefaultAc(userId)

        #! If user has an account
        if ac:
            #! If the text is a valid url or magnet link
            if magnetLink or message.text.startswith('http') or 'magnet:?' in message.text:
                #! Add torrent in the account

                #!? If torrent is added via start paramater
                if magnetLink:
                    sent = bot.edit_message_text(text=language['collectingInfo'][userLanguage], chat_id=message.chat.id, message_id=messageId)
                
                #!? If torrent is added via direct message
                else:
                    sent = bot.send_message(message.chat.id, language['collectingInfo'][userLanguage])
                
                account = Seedr(cookie=ac['cookie'])
                response = account.addTorrent(magnetLink or message.text).json()
                
                #! If torrent added successfully
                if 'user_torrent_id' in response:
                    startTime = time()
                    torrentId = response['user_torrent_id']
                    
                    cancelMarkup = telebot.types.InlineKeyboardMarkup()
                    cancelMarkup.add(telebot.types.InlineKeyboardButton(text=language['cancelBtn'][userLanguage], callback_data=f'cancel_{torrentId}'))
                    
                    bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=f"⬇️ <b>{response['title']}</b>", reply_markup=cancelMarkup)
                    
                    queue = account.listContents().json()

                    #!? Getting the progressUrl from active torrents list
                    progressUrl = None
                    if queue['torrents']:
                        for torrent in queue['torrents']:
                            if torrentId == torrent['id']:
                                progressUrl = torrent['progress_url']

                    #! If progressUrl is found
                    if progressUrl:
                        bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=f"⬇️ <b>{response['title']}</b>\n\n{language['collectingSeeds'][userLanguage]}", reply_markup=cancelMarkup)
                        progressPercentage = 0
                        oldText = ''
                        
                        ## [Alert] Must change this algorithm
                        #! Collecting seeds
                        for i in range(2, 60):
                            progressResponse = json.loads(requests.get(progressUrl).text[2:-1])
                            
                            #! Break if seeds are collected
                            if 'title' in progressResponse:
                                break
                            
                            #! Increase the amount of sleep in each iteration
                            #sleep(i)
                            await asyncio.sleep(i)
                            
                        #! If seeds collected successfully
                        if 'title' in progressResponse:
                            downloadComplete = False

                            ## [Alert] Must change this algorithm
                            #! Updating download status
                            for _ in range(500):
                                progressPercentage =  progressResponse['progress']
                                text = f"<b>⬇️ {progressResponse['title']}</b>\n\n"
                                
                                #! If download finished
                                if progressResponse['progress'] == 101:
                                    text = f"<b>📁 {progressResponse['title']}</b>\n\n"
                                    
                                    bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=f"{text}{language['copyingToFolder'][userLanguage]}", reply_markup=cancelMarkup)
                                    
                                    copyFlag = False
                                    ## [Alert] Must change this algorithm
                                    for _ in range(2,60):
                                        progress = requests.get(progressUrl).text[2:-1]
                                        progress = json.loads(progress)

                                        if 'folder_created' in progress:
                                            text += f"{language['files'][userLanguage]} /getFiles_{progress['folder_created']}\n{language['link'][userLanguage]} /getLink_{progress['folder_created']}\n{language['delete'][userLanguage]} /delete_{progress['folder_created']}\n\n"
                                            text += language['downloadFinishedIn'][userLanguage].format(convertTime(time() - startTime))
                                            
                                            markup = telebot.types.InlineKeyboardMarkup()
                                            markup.add(telebot.types.InlineKeyboardButton(text=language['openInPlayer'][userLanguage], callback_data=f"getPlaylist_folder_{progress['folder_created']}"))
                                            markup.add(telebot.types.InlineKeyboardButton(text=language['joinChannelBtn'][userLanguage], url='t.me/h9youtube'), telebot.types.InlineKeyboardButton(text=language['joinDiscussionBtn'][userLanguage], url='t.me/h9discussion'))
                                            
                                            bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=text, reply_markup=markup)
                                            
                                            downloadComplete = True
                                            copyFlag = True
                                            
                                            break
                                        else:
                                            #sleep(5)
                                            await asyncio.sleep(5)
                                    
                                    if not copyFlag:
                                        bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['delayWhileCopying'][userLanguage], reply_markup=cancelMarkup)
                                    
                                    break
                                
                                #!? If downloading, update the status
                                else:
                                    text += f"{language['size'][userLanguage]} {convertSize(progressResponse['size'])}\n{language['torrentQuality'][userLanguage]} {progressResponse['torrent_quality']}\n{language['seeders'][userLanguage]} {progressResponse['stats']['seeders']}\n{language['leechers'][userLanguage]} {progressResponse['stats']['leechers']}\n{language['downloadingFrom'][userLanguage]} {progressResponse['stats']['downloading_from']}\n{language['uploadingTo'][userLanguage]} {progressResponse['stats']['uploading_to']}\n"
                                    text += f"{language['rate'][userLanguage]} {convertSize(progressResponse['download_rate'])}/sec \n{language['percentage'][userLanguage]} {round(float(progressPercentage), 2)}%\n\n{progressBar(progressPercentage)}"
                                
                                    #! Show warnings
                                    # if progressResponse['warnings'] != '[]':
                                    #     warnings = progressResponse['warnings'].strip('[]').replace('"','').split(',')
                                    #     for warning in warnings:
                                    #         text += f"\n⚠️ {warning.capitalize()}"
                                    
                                    
                                    #! Only edit the text if the response changes
                                    if oldText != text:
                                        bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=text, reply_markup=cancelMarkup)
                                        oldText = text
                                    
                                    #sleep(3)
                                    await asyncio.sleep(3)
                                    progressResponse = json.loads(requests.get(progressUrl).text[2:-1])
                            
                            #! If download is taking long time
                            if not downloadComplete:
                                bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['delayWhileDownloading'][userLanguage], reply_markup=cancelMarkup)
                                    
                        #! If seeds collecting is taking long time
                        else:
                            bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['delayWhileCollectingSeeds'][userLanguage], reply_markup=cancelMarkup)
                    
                    #! If failed to find progressUrl
                    else:
                        exceptions(message, response, userLanguage)

                #! If no enough space
                elif response['result'] == 'not_enough_space_added_to_wishlist':
                    bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['noEnoughSpace'][userLanguage])

                #! Invalid magnet link
                elif response['result'] == 'parsing_error':
                    invalidMagnet(message, userLanguage, sent.id)
                
                #! If parallel downloads exceeds
                elif response['result'] == 'queue_full_added_to_wishlist':
                    bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['parallelDownloadExceed'][userLanguage])

                #! If the torrent is already downloading
                elif response == {'result': True}:
                    bot.edit_message_text(chat_id=message.chat.id, message_id=sent.id, text=language['alreadyDownloading'][userLanguage])
                
                else:
                    exceptions(message, response, userLanguage)
            
            #! Invalid magnet link
            else:
                invalidMagnet(message, userLanguage)
            
        #! If no accounts
        else:
            noAccount(message, userLanguage)

def invalidMagnet(message, userLanguage, message_id=None):
    markup = telebot.types.InlineKeyboardMarkup()

    params = base64.b64encode(message.text.encode('utf-8')).decode('utf-8')
    params = f'?start={params}' if len(params) <= 64 else ''
        
    markup.add(telebot.types.InlineKeyboardButton(text='Torrent Hunt 🔎', url=f'https://t.me/torrenthuntbot{params}'))
    
    #! If message_id is passwd, edit the message
    if message_id:
        bot.edit_message_text(chat_id=message.chat.id, message_id=message_id, text=language['invalidMagnet'][userLanguage], reply_markup=markup)
    
    #! Else, send a new message
    else:
        bot.send_message(chat_id=message.chat.id, text=language['invalidMagnet'][userLanguage], reply_markup=markup)