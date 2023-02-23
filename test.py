# coding: utf-8
import pandas as pd
import numpy as np
import random

import telebot
from telebot import types
import requests

import data_load as dl

settings = dl.read_yaml_config('config.yaml', section='telegram')

l = dl.get_data("""
                with 
                base as 
                (
                    select item, rating, insert_time, max(insert_time) over (partition by item) as fresh_time
                    from tl.rating_history
                )
                select item, rating
                from base
                where fresh_time = insert_time
                order by rating desc
""")
                
l = dl.get_data("""

    select distinct user--, avg(result)
    from tl.game_results
    --where user='vladchernichenko'
    --group by user


""")

print(l)

token = settings['token']
bot = telebot.TeleBot(token)

@bot.message_handler(commands=["start"])
def start(m, res=False):
    bot.send_message(m.chat.id, 'Я на связи. Напиши мне что-нибудь )')


@bot.message_handler(content_types=["text"])
def handle_text(message):
    answ = message.text
    c1, c2 = answ.split(' ')
    res = float(c1) + float(c2)
    output = 'Сумма: ' + str(res)

    df = pd.DataFrame([c1], columns=['value'])
    dl.insert_data(df, 'tl', 'telebot_test_002')

    bot.send_message(message.chat.id, output)


# bot.polling(none_stop=True, interval=0)


