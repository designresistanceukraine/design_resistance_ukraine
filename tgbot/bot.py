#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

msg_welcome = "Hi, I am bot that helps DRUA to manage files.\n\nYou can send me a file as simply as an attachment - no hashtags, no coding magic ... as easy as it can be!\n"
msg_help = "1. Click an attachment button which is next to a text message field\n2. Choose your file\n3. Open\n4. Send!\n"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    '''update.message.reply_markdown_v2(
        fr'Hola {user.mention_markdown_v2()}\!',
        reply_markup=ForceReply(selective=True),
    )'''
    update.message.reply_text(msg_welcome + '\n' + msg_help)


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text(msg_help)


def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def upload(update: Update, context: CallbackContext) ->None:
    """Upload a file to the storage"""
    
    print("\n\nUpload...")
    file_id = update.message.document.file_id
    file_name =  update.message.document.file_name
    
    print("", file_id, file_name)

    # path to the storage in a format C:/TEMP/
    path_storage = "PATH"
    with open('path_storage.secret') as f:
        path_storage = f.readline()
        
    print(path_storage)
    file = context.bot.get_file(file_id)

    file.download(path_storage+file_id+file_name)
    
def downloader(update, context):
    context.bot.get_file(update.message.document).download()
    
    print("\n\ntrying to download the file", )
    # writing to a custom file
    with open("output.txt", 'wb') as f:
        context.bot.get_file(update.message.document).download(out=f)
        
    print(update.message)
    #file_id = message.voice.file_id
    #newFile = bot.get_file(file_id)
    #newFile.download('voice.ogg')

'''
{'group_chat_created': False, 'document': {'file_name': 'testbot.txt', 'mime_type': 'text/plain', 'file_size': 7, 'file_id': 'BQACAgIAAxkBAAMdYiY3l1Cw7CEunj0llm1YctuvnuYAAl8XAALk2TBJKDygbUFN9LkjBA', 'file_unique_id': 'AgADXxcAAuTZMEk'}, 'chat': {'last_name': 'Radomskyi', 'type': 'private', 'username': 'Ambreaux', 'first_name': 'Oleksandr', 'id': 344195365}, 'delete_chat_photo': False, 'photo': [], 'channel_chat_created': False, 'date': 1646671767, 'message_id': 29, 'caption_entities': [], 'new_chat_members': [], 'new_chat_photo': [], 'supergroup_chat_created': False, 'entities': [], 'from': {'username': 'Ambreaux', 'first_name': 'Oleksandr', 'language_code': 'en', 'id': 344195365, 'is_bot': False, 'last_name': 'Radomskyi'}}
'''


def main() -> None:
    """Start the bot."""
    
    token = "TOKEN"
    with open('token.secret') as f:
        token = f.readline()
    
    # Create the Updater and pass it your bot's token.
    updater = Updater(token, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("upload", upload))
    

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    #dispatcher.add_handler(MessageHandler(Filters.document, downloader))
    dispatcher.add_handler(MessageHandler(Filters.document, upload))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()



if __name__ == '__main__':
    main()
