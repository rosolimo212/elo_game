# coding: utf-8
# ELO-bot main file
import telebot
from telebot import types

import pandas as pd
import numpy as np
import random

# module for working with SQL
import data_load as dl
settings = dl.read_yaml_config('config.yaml', section='telegram')










# telegram bot logic
def make_button(button_name, markup):
    item=types.KeyboardButton(button_name)
    markup.add(item)
    
    return markup 

def launch_new_game(bot, message, markup):
       bot.send_message(
                message.chat.id, 
                """
                New game module
                """,
                reply_markup=markup
                        )


def launch_ratings(bot, message, markup):
       bot.send_message(
                message.chat.id, 
                """
                Ratings
                """,
                reply_markup=markup
                        )
       
def launch_personal_stat(bot, message, markup):
       bot.send_message(
                message.chat.id, 
                """
                Personal stat
                """,
                reply_markup=markup
                        )
       
def launch_leaderboard(bot, message, markup):
       bot.send_message(
                message.chat.id, 
                """
                Leaderboard
                """,
                reply_markup=markup
                        )

def launch_404(bot, message, markup):
       bot.send_message(
                message.chat.id, 
                """
                Something went wrong
                """,
                reply_markup=markup
                        )







markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
bot = telebot.TeleBot(settings['token'])






@bot.message_handler(commands=["start"])
def launch_main_menu(message):
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup = make_button('New game', markup)
    markup = make_button('Show book rating', markup)
    markup = make_button('Show leaderboard', markup)
    markup = make_button('Show my personal statistics', markup)
    
    bot.send_message(
        message.chat.id, 
        """
        Hi! Lets' play a game?
        """,
        reply_markup=markup
                )

@bot.message_handler(content_types=["text"])
def handle_text(message):
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    if message.text.strip() == 'New game':
        launch_new_game(bot, message, markup)
    elif message.text.strip() == 'Show book rating':
        launch_ratings(bot, message, markup)
    elif message.text.strip() == 'Show leaderboard':
        launch_leaderboard(bot, message, markup)
    elif message.text.strip() == 'Show my personal statistics':
        launch_personal_stat(bot, message, markup)
    elif message.text.strip() == 'Main menu':
        launch_main_menu(message)
    else:
        launch_404(bot, message, markup)









print('Ready for launch')
bot.polling(none_stop=True, interval=0)



