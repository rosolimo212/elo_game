# # coding: utf-8
import pandas as pd
import numpy as np
import random

import telebot
from telebot import types
import requests
import time

import data_load as dl

settings = dl.read_yaml_config('config.yaml', section='telegram')



token = settings['token']
bot = telebot.TeleBot(token)

def send_alive_message():
    while True:
        bot.send_message(chat_id=249792088, text="Bot is stiil alive!")
        time.sleep(1)

@bot.message_handler(commands=["start"])
def start(m, res=False):
    bot.send_message(m.chat.id, 'Я на связи. Напиши мне что-нибудь )')
    send_alive_message()


@bot.message_handler(content_types=["text"])
def handle_text(message):
    answ = message.text
    c1, c2 = answ.split(' ')
    res = float(c1) + float(c2)
    output = 'Сумма: ' + str(res)

    bot.send_message(message.chat.id, output)

bot.polling(none_stop=True, interval=0)

    



# l = dl.get_data("""
#                 with 
#                 base as 
#                 (
#                     select item, rating, insert_time, max(insert_time) over (partition by item) as fresh_time
#                     from tl.rating_history
#                 )
#                 select item, rating
#                 from base
#                 where fresh_time = insert_time
#                 order by rating desc
# """)
                
# l = dl.get_data("""

#                 select *
#                 from tl.events

#                 limit 5



# """)

# print(l)

