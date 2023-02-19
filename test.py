# coding: utf-8
import pandas as pd
import numpy as np
import random

import telebot
from telebot import types
import requests

import data_load as dl



token = '5859091834:AAG5E0DoKe366ga67vEfD0HrJUcpw-svudQ'
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


bot.polling(none_stop=True, interval=0)