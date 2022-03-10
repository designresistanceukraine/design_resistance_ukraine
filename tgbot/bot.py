import hashlib
import re
import os
from datetime import datetime
import logging

from telegram import Update, ForceReply, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

#def create_gauth_settings_yaml():
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
#print(gauth_settings_yaml,'\n')
#print("creating yaml")
with open('settings.yaml', 'w') as f:
    f.write(gauth_settings_yaml)

#print("creating yaml done")

'''
credentials = os.environ.get('GAUTH_CREDENTIALS')
print(credentials)
with open('credentials.json', 'w') as f:
    f.write(credentials)
    
print("creating json done")
'''

gauth = GoogleAuth()
#print("gauth", gauth)
drive = GoogleDrive(gauth)
#print("gdrive", drive)

text_button_start = 'Почати'
buttons = [[KeyboardButton(text_button_start)]]

msg_about = '''Biтаю!

Я бот Об'єднаних Дизайн Сил Україні.
Зі мною ти можеш долучитися до Спротиву російскій Агресії за допомогою своєї творчості.

Наразі я пидтримую наступні типи файлів:
• JPG
• JPEG
• PNG

Але не більші за 2 мегабайти.

Ти можеш видправити як файл так і зображення, то зовсім не принципово.

Будь які інші типи файлів, або файли більші за 2 мегабайти, я просто проігнорую.
'''


msg_welcome_en = '''Hi!'''
msg_welcome_ua = '''<b>Biтаю!</b>'''

msg_help = '''For the moment we support only several commontly used raster image file formats and plain text\n''' + \
'''For the security reasons file size is limited, and I will not respond if you send me messages too fast\n''' + \
'''\nDrag-and-drop(or attach) your file or photo into this chat window, that is it!\n'''+ \
'''\nI will not respond to your messages other than plaint text files, images or photos.\n''' + \
'''\nIf you want, you can attach your files:\n'''+ \
'''1. Click an attachment button which is next to a text message field\n'''+ \
'''2. Choose your file or photo\n''' + \
'''3. Open\n''' + \
'''4. Send\n'''

'''Я бот Об'єднаних Дизайн Сил Україні.
Зі мною ти можеш долучитися до Спротиву російскій Агресії за допомогою своєї творчості.

'''

msg_help_ua = '''Наразі я пидтримую наступні типи файлів:
• JPG
• JPEG
• PNG

Але не більші за 2 мегабайти.

Ти можеш видправити як файл так і зображення, то зовсім не принципово.

Будь які інші типи файлів, або файли більші за 2 мегабайти, я просто проігнорую.
'''

'''
___

Будь ласка почекай трохи, ми завантажумо твій внесок до нашої перемоги.

___
Дякую з твою допомогу. Все буде Украна 🤟🏻🇺🇦

Перевір @DesignResistanceUA, наш головний канал, трохи пізніше. Досить їмовірно що твій арт з’явиться там.
'''

msg_success_en = "Success!\n\nFile uploaded to the DRUA Storage! :)\n\nVive la Résistance!"
msg_in_progress_en = "Uploading(please be patient) file:\n"
msg_error_header_en = "I cannot process your file :(\n"

msg_in_progress_ua = '''___
Будь ласка почекай трохи, ми завантажуємо твій внесок до нашої перемоги.
___'''

msg_success_ua = '''Дякую з твою допомогу. Все буде Украна 🤟🏻🇺🇦

Перевір @DesignResistanceUA, наш головний канал, трохи пізніше. Досить їмовірно що твій арт з’явиться там.
'''

msg_error_body = {
      1 : '\nI can open only raster images and plain text. Please make sure you can open your file with the default file viewer on you device.\n'
    , 2 : '\nYour file seems to be too large.'
    , 3 : '\nThis file already in my storage!'
    , 255: '\nUnexpected error :/'
}


msg_welcome = msg_welcome_ua
msg_help = msg_help_ua

msg_success = msg_success_ua
msg_in_progress = msg_in_progress_ua

#msg_error_header = "I cannot process your file :(\n"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def gdrive_upload_file(file_name):
    parent_key_data = os.environ.get('GDRIVE_PARENT_KEY')

    #for upload_file in upload_file_list:
    gfile = drive.CreateFile({'parents': [{'id': parent_key_data}]})
    # Read file and set it as the content of this instance.
    gfile.SetContentFile(file_name)
    gfile.Upload() # Upload the file.

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
 
    #print(gfile_list)
    #for gfile in gfile_list:
    #    print('title: %s, id: %s' % (gfile['title'], gfile['id']))

    file_uid = file.file_unique_id
    file_hash = file.file_hash

    #print('uid',file_uid)
    #print('file_hash',file_hash)

    result = [f for f in gfile_list if re.search(r'('+file_hash+'|'+file_uid+').*$', f['title'])]
    #for v in result:
    #    print(v)

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

# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    msg = update.message
    context.bot.send_message(chat_id = update.effective_chat.id
        , text=str(msg_help) #msg_welcome
        , reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        , parse_mode=ParseMode.HTML #ParseMode.MARKDOWN_V2#ParseMode.HTML
    )
    #msg.reply_text(msg_help, parse_mode="Markdown")


def message_handler(update: Update, context: CallbackContext) -> None:
    msg = update.message
    
    if text_button_start in msg.text:
        user = update.effective_user

        context.bot.send_message(chat_id = update.effective_chat.id
        , text=str(msg_help) #msg_welcome
        , reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        , parse_mode=ParseMode.HTML #ParseMode.MARKDOWN_V2#ParseMode.HTML
        )
        #msg.reply_text(msg_help,parse_mode="Markdown")
        
def upload(update: Update, context: CallbackContext) -> None:
    """Upload a file to the storage"""
    msg = update.message
    #print('msg', msg)
    n_photos = len(msg.photo)

    data = None
    if 0 < n_photos:
        #print(n_photos)
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

    #print("message:", unix_date, user_name, file_name)
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

        #cwd = os.getcwd()
        #print(cwd)
        #print('before download', os.listdir(cwd))

        file.download(file_storage_path) # store file locally      
        #print('after download', os.listdir(cwd))

        try:
            gdrive_upload_file(file_storage_path) # upload to gdrive
        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)   # arguments stored in .args
            print(e)        # __str__ allows args to be printed directly,
                            # but may be overridden in exception subclasses
            '''
            msg.reply_text(msg_error_header + '\n' \
                + file_name + '\n' \
                + msg_error_body[err])
            '''
            
        else:
            #print('gdrive_upload_file() success!')
            msg.reply_text(msg_success, parse_mode="Markdown")
        finally:
            #print('gdrive_upload finished, cleaning up.')
            #print('before clean-up',os.listdir(cwd))
            os.remove(file_storage_path) # remove local copy of a file
            #print('after clean-up',os.listdir(cwd))
    else:
        pass
        '''
        msg.reply_text(msg_error_header + '\n' \
            + file_name + '\n' \
            + msg_error_body[err])
        '''
        
def main() -> None:
    """Start the bot."""
    token = os.environ.get('TOKEN')


    # Create the Updater and pass it your bot's token.
    updater = Updater(token, use_context=True)
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text, message_handler))
    dispatcher.add_handler(MessageHandler(Filters.document | Filters.photo, upload))

    #updater.start_polling()
    port = int(os.environ.get('PORT', 80))
    webhook = os.environ.get('WEBHOOK_URL')
    updater.start_webhook(listen="0.0.0.0",
                          port=int(port),
                          url_path=token,
                          webhook_url = webhook + token )

    updater.idle()

if __name__ == '__main__':
    main()