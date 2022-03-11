import hashlib
import re
import os
from datetime import datetime
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

msg_help = '''Наразі я пидтримую наступні типи файлів:
• JPG
• JPEG
• PNG

Але не більші за 2 мегабайти.

Ти можеш видправити як файл так і зображення, то зовсім не принципово.

Будь які інші типи файлів, або файли більші за 2 мегабайти, я просто проігнорую.
'''

msg_in_progress = '''___
Будь ласка почекай трохи, ми завантажуємо твій внесок до нашої перемоги.
___'''

msg_success = '''Дякую з твою допомогу. Все буде Украна 🤟🏻🇺🇦

Перевір @DesignResistanceUA, наш головний канал, трохи пізніше. Досить їмовірно що твій арт з’явиться там.
'''

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def gdrive_upload_file(file_name):
    parent_key_data = os.environ.get('GDRIVE_PARENT_KEY')
    gfile = drive.CreateFile({'parents': [{'id': parent_key_data}]})
    gfile.SetContentFile(file_name)
    gfile.Upload()

def get_filecontent_hash(filename):
    sha256_hash = hashlib.sha256()
    with open(filename,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)

    return str(sha256_hash.hexdigest())

def get_datafile(file_name):
    res = "data"
    with open(file_name) as f:
        res = f.readline()
    return res

def check_mime_type(file):
    mime_type = file.mime_type
    supported_file_types = get_datafile('mime_filetypes')
    return mime_type in supported_file_types

def check_size(file):
    size = int(file.file_size)
    supported_file_size = int(get_datafile('filesize'))
    return size <= supported_file_size

def check_file_exists(file):
    # TODO:
    # this is potential memory and speed bottleneck
    # need to use database instead of listing files every time

    parent_key_data = os.environ.get('GDRIVE_PARENT_KEY')
    gfile_list = None
    try:
        gfile_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(parent_key_data)}).GetList()
    except:
        print("Cannot connect to the storage!")
        return 1

    file_uid = file.file_unique_id
    file_hash = file.file_hash

    result = [f for f in gfile_list if re.search(r'('+file_hash+'|'+file_uid+').*$', f['title'])]

    return 0 == len(result) or 0 == len(gfile_list)

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
    user = update.effective_user
    msg = update.message
    context.bot.send_message(chat_id = update.effective_chat.id
        , text=str(msg_help)
        , reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        , parse_mode=ParseMode.HTML
    )

def message_handler(update: Update, context: CallbackContext) -> None:
    msg = update.message
    
    if text_button_start in msg.text:
        user = update.effective_user

        context.bot.send_message(chat_id = update.effective_chat.id
        , text=str(msg_help)
        , reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        , parse_mode=ParseMode.HTML
        )

def upload(update: Update, context: CallbackContext) -> None:
    """Upload a file to the storage"""
    msg = update.message
    n_photos = len(msg.photo)

    data = None
    if 0 < n_photos:
        i_last_photo = n_photos - 1
        data = msg.photo[i_last_photo]
        data.file_name = 'photo.jpg'
        data.mime_type = 'image/jpg'
    else:
        data = msg.document
    
    unix_date = str(datetime.timestamp(msg.date))
    user_name = msg.chat.username
    file_id = data.file_id
    file_uid = data.file_unique_id
    file_name = data.file_name

    msg.reply_text(msg_in_progress, parse_mode="Markdown")
    
    file = context.bot.get_file(file_id)
    
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

        try:
            gdrive_upload_file(file_storage_path) # upload to gdrive
        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)   # arguments stored in .args
            print(e)        # __str__ allows args to be printed directly,
                            # but may be overridden in exception subclasses            
        else:
            msg.reply_text(msg_success, parse_mode="Markdown")
        finally:
            os.remove(file_storage_path) # remove local copy of a file
    else:
        pass

def main() -> None:
    """Start the bot."""
    token = os.environ.get('TOKEN')
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text, message_handler))
    dispatcher.add_handler(MessageHandler(Filters.document | Filters.photo, upload))

    port = int(os.environ.get('PORT', 80))
    webhook = os.environ.get('WEBHOOK_URL')

    updater.start_webhook(listen="0.0.0.0",
                          port=int(port),
                          url_path=token,
                          webhook_url = webhook + token )

    updater.idle()

if __name__ == '__main__':
    main()