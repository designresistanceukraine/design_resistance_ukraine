import hashlib
import re
import os
from time import sleep
from datetime import datetime
from random import randint

import logging

from telegram import Update, ForceReply, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth_settings_yaml = '''
client_config_backend: settings
client_config:
  client_id: '''+os.environ.get('GAUTH_CLIENT_ID')+'''
  client_secret: '''+os.environ.get('GAUTH_CLIENT_SECRET')+'''

save_credentials: True
save_credentials_backend: file
save_credentials_file: credentials.json

get_refresh_token: True

oauth_scope:
  - https://www.googleapis.com/auth/drive.file
  '''

with open('settings.yaml', 'w') as f:
    f.write(gauth_settings_yaml)

'''
credentials = os.environ.get('GAUTH_CREDENTIALS')
print(credentials)
with open('credentials.json', 'w') as f:
    f.write(credentials)
    
print("creating json done")
'''

gauth = GoogleAuth()
drive = GoogleDrive(gauth)


text_button_start = 'Почати'
buttons = [[KeyboardButton(text_button_start)]]

# TODO: later when multiple languases woul be supported, 
# move messages to a separate class

msg_help = '''Наразі я підтримую наступні типи файлів:
• JPG
• JPEG
• PNG

Але не більші за 10 мегабайт.

Ти можеш видправити як файл так і зображення, то зовсім не принципово.

До всього, що ти менi вiдправиш, можна додавати опис - я також зберiгатиму твої повiдомлення.

Будь які інші типи файлів, або файли більші за 10 мегабайт, я просто проігнорую.
'''

msg_in_progress = '''___
Будь ласка почекай трохи, ми завантажуємо твій внесок до нашої перемоги.
___'''

msg_success = '''Дякую з твою допомогу. Все буде Україна 🤟🏻🇺🇦

Перевір @DesignResistanceUA, наш головний канал, трохи пізніше. Досить їмовірно що твій арт з’явиться там.
'''

logging.basicConfig(
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    , level=logging.INFO)

logger = logging.getLogger(__name__)

class Constants:
    str_user_name = 'username'
    str_user_id = 'userid'
    str_user_firstname = 'userfname'
    str_user_lastname = 'userlname'
    str_photo_mimetype = 'image/jpg'
    str_photo_name = 'photo.jpg'
    str_file_name = 'file.jpg'
    str_file_description_name = 'description.txt'
    str_file_id = 'fileid'
    str_file_uid = 'fileuid'
    str_file_hash = 'filehash'
    str_data = 'data'
    str_description = '/description'
    filename_ban = 'ban'
    filename_mime_filetypes = 'mime_filetypes'
    filename_filesize = 'filesize'
    filename_sleep_delay = 'sleep_delay'
    env_data_folder_key = 'GDRIVE_PARENT_KEY'

constants = Constants()

#load static things in advance
parent_key_data = os.environ.get(constants.env_data_folder_key)

def int2str_safe(i):
    s = 'none'
    try:
        s = str(i)
    except:
        pass
    
    return s

def str_concat_safe(first, second, default):
    try:
        first = first + second
    except:
        first = first + default
    return first
    
def gdrive_upload_file(file_name):
    try:
        gfile = drive.CreateFile({'parents': [{'id': parent_key_data}]})
        gfile.SetContentFile(file_name)
        gfile.Upload()
        #gdrive_upload_file(file_storage_path) # upload to gdrive
    except Exception as e:
        print(type(e))  # the exception instance
        print(e.args)   # arguments stored in .args
        print(e)        # __str__ allows args to be printed directly,
                        # but may be overridden in exception subclasses            
    else:
        pass
    finally:
        pass

def get_filecontent_hash(filename):
    s = constants.str_file_hash
    try:
        sha256_hash = hashlib.sha256()
        with open(filename,"rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
        try:
            s = str(sha256_hash.hexdigest())
        except:
            pass
    except:
        pass
    
    return s

def get_datafile(file_name):
    res = constants.str_data
    
    try:
        with open(file_name) as f:
            res = f.readline()
    except Exception as e:
        print(e)

    return res

def save_text(text, file_name):
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            res = f.write(text)
    except Exception as e:
        print(e)
        
def pretend_working(message):
    message.reply_text(msg_in_progress, parse_mode="Markdown")
    sleep(randint(1,997) / 103)
    message.reply_text(msg_success, parse_mode="Markdown")
    
def ckeck_user_banned(chat):
    # TODO: maybe move file with banned users to gdrive?
    if str_concat_safe('', chat.username, constants.str_user_name) in ban:
        return True
    if str_concat_safe('', int2str_safe(chat.id), constants.str_user_id) in ban:
        return True
    if str_concat_safe('', chat.first_name, constants.str_user_firstname) in ban:
        return True
    if str_concat_safe('', chat.last_name, constants.str_user_lastname) in ban:
        return True

    return False

def check_mime_type(file):
    mime_type = file.mime_type
    return mime_type in supported_file_types

def check_size(file):
    size = int(file.file_size)
    return size <= supported_file_size

def check_file_exists(file):
    # TODO:
    # this is potential memory and speed bottleneck
    # need to use database instead of listing files every time
    gfile_list = None
    try:
        gfile_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(parent_key_data)}).GetList()
    except Exception as e:
        print("Cannot connect to the storage!", e)
        return 1

    file_uid = str_concat_safe('', file.file_unique_id, constants.str_file_uid)
    file_hash = str_concat_safe('', file.file_hash, constants.str_file_hash) 

    result = [f for f in gfile_list if re.search(r'('+file_hash+'|'+file_uid+').*$', f['title'])]
    return 0 == len(result) or 0 == len(gfile_list)

def get_username_id(message):
    c = message.chat
    result = ''
    result = str_concat_safe(result, c.username, constants.str_user_name) + '_'
    result = str_concat_safe(result, int2str_safe(c.id), constants.str_user_id) + '_'
    result = str_concat_safe(result, c.first_name, constants.str_user_firstname) + '_'
    result = str_concat_safe(result, c.last_name, constants.str_user_lastname)
    return result

def check_file(file):
    # todo: write proper error handling
    # rewrite errors into int bits instead of different int for each error
    if not check_mime_type(file):
        return 1

    if not check_size(file):
        return 2

    if not check_file_exists(file):
        return 3

    return 0

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    msg = update.message
    context.bot.send_message(chat_id = update.effective_chat.id
        , text=str(msg_help)
        , reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        , parse_mode=ParseMode.HTML)

def message_handler(update: Update, context: CallbackContext) -> None:
    #print("updaload", datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    sleep(sleep_delay)
    #print("updaload", datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

    msg = update.message
    print(msg)

    if text_button_start in msg.text:
        context.bot.send_message(chat_id = update.effective_chat.id
        , text=str(msg_help)
        , reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        , parse_mode=ParseMode.HTML)
    else:
        #if constants.str_description in msg.text:
        user_name = get_username_id(msg)
        unix_date = int2str_safe(datetime.timestamp(msg.date))
        file_description_storage_path = unix_date + '_' + \
            user_name + '_' + \
            constants.str_file_description_name
        
        text = msg.text #.replace(constants.str_description, '')
        save_text(text, file_description_storage_path)
        gdrive_upload_file(file_description_storage_path)
        os.remove(file_description_storage_path) # remove local copy of a file

        msg.reply_text(msg_success, parse_mode="Markdown")


def upload(update: Update, context: CallbackContext) -> None:
    """Upload a file to the storage"""
    #print("updaload", datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    sleep(sleep_delay)
    #print("updaload", datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    msg = update.message
    print(msg)
    
    # keep banned users away
    # do not let them change attack technique
    if ckeck_user_banned(msg.chat):
        pretend_working(msg)
        return

    # telegram seems to be sending pyramid of 4 photos of different resolution
    # when photos sent without compression and 2 photos when 'compress'
    n_photos = len(msg.photo)

    data = None
    if 0 < n_photos:
        i_last_photo = n_photos - 1 # get the last photo - highest quaity
        data = msg.photo[i_last_photo]
        data.file_name = constants.str_photo_name
        data.mime_type = constants.str_photo_mimetype
    else:
        data = msg.document

    user_name = get_username_id(msg)
    file_id = str_concat_safe('', data.file_id, constants.str_file_id)
    file_uid = str_concat_safe('', data.file_unique_id, constants.str_file_uid)
    file_name = str_concat_safe('', data.file_name, constants.str_file_name)

    msg.reply_text(msg_in_progress, parse_mode="Markdown")

    file = context.bot.get_file(file_id)

    unix_date = int2str_safe(datetime.timestamp(msg.date))
    #print(unix_date, user_name, file_uid, file_name)

    file_tmp = unix_date + '_' + \
        user_name + '_' + \
        file_uid + '_' + \
        file_name

    file.download(file_tmp) # create temp file in current working directory /app
    file_hash = get_filecontent_hash(file_tmp) # get hash
    os.remove(file_tmp) # remove temp file
    data.file_hash = file_hash # add file hash to the document object
    err = check_file(data) # check if everything is ok with the file

    if(0 == err):
        file_storage_path = unix_date + '_' + \
            user_name + '_' + \
            file_hash + '_' + \
            file_name

        file.download(file_storage_path) # store file locally
        gdrive_upload_file(file_storage_path)
        os.remove(file_storage_path) # remove local copy of a file

        if msg.caption:
            file_description_storage_path = unix_date + '_' + \
            user_name + '_' + \
            file_hash + '_' + \
            constants.str_file_description_name

            save_text(msg.caption, file_description_storage_path)
            gdrive_upload_file(file_description_storage_path)
            os.remove(file_description_storage_path) # remove local copy of a file
    else:
        pass

    msg.reply_text(msg_success, parse_mode="Markdown")

def main() -> None:
    """Start the bot."""
    token = os.environ.get('TOKEN')
    workers = 1 # use only single thread for each chat, default is 4

    request_kwargs = { 
          'con_pool_size' : 1 #Number of connections to keep in the connection pool
        , 'connect_timeout' : 3.0 #The maximum amount of time (in seconds) to wait for a connection attempt to a server to succeed
        , 'read_timeout' : 3.0 #The maximum amount of time (in seconds) to wait between consecutive read operations for a response from the server.
    }

    updater = Updater(token
        , use_context=True
        , workers=workers
        , request_kwargs=request_kwargs)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text, message_handler))
    dispatcher.add_handler(MessageHandler(Filters.document | Filters.photo, upload))

    port = int(os.environ.get('PORT', 80))
    webhook = os.environ.get('WEBHOOK_URL')

    updater.start_webhook(listen="0.0.0.0",
                          port=int(port),
                          url_path=token,
                          webhook_url = webhook + token)

    updater.idle()

ban = get_datafile(constants.filename_ban)
supported_file_types = get_datafile(constants.filename_mime_filetypes)
supported_file_size = int(get_datafile(constants.filename_filesize))
sleep_delay = float(get_datafile(constants.filename_sleep_delay))


if __name__ == '__main__':
    main()