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

topics_dct = {
    'Популярные': 'is_popular', 
    'Фантастика': 'is_fantastic',
    'Классика': 'is_classic',
            }
topics_lst = list(topics_dct.keys())
topic = ''
bot = telebot.TeleBot(settings['token'])


# loggin functions
def make_event_log(message, event_name, params):
    user = message.from_user.username
    user_id = message.from_user.id

    log_lst = [user_id, user, event_name, params]
    log_df = pd.DataFrame([log_lst])
    log_df.columns = ['user_id', 'user_name', 'event_name', 'parameters']
    # dl.insert_data(log_df, 'tl', 'events')


# telegram bot logic
def make_answer_buttons(buttons_lst):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons_lst:
        item = types.KeyboardButton(button)
        markup.add(item)
    
    return markup 

def choise_category(bot, message):
    buttons = topics_lst.copy()
    buttons.append('Главное меню')
    markup = make_answer_buttons(buttons)

    bot.send_message(
            message.chat.id, 
            """
            Выберете категорию
            """,
            reply_markup=markup
                    )
    
def start_game(bot, message, topic):
    items = dl.get_data("""
                    select item_name
                    from tl.items
                    where {slice} = 1
                    """.format(
                        slice = topics_dct[topic]
                              ))['item_name'].values
    print(items)


    markup = make_answer_buttons([
         'Верхний',
         'Нижний',
         'Пропустить',
                                ])

    bot.send_message(
            message.chat.id, 
            """
            Выберете то, что вам нравится больше
            """,
            reply_markup=markup
                    )
    return topic
    
def skip_game(bot, message):
    markup = make_answer_buttons([
         'Продолжить',
         'Показать мою статистику',
         'Главное меню',
                                ])
    answer = """
Пропустим, никаких проблем
    """

    bot.send_message(
            message.chat.id, 
            answer,
            reply_markup=markup
                    )
    
    
def finish_game(bot, message):
        markup = make_answer_buttons([
            'Продолжить',
            'Показать мою статистику',
            'Главное меню',
                                    ])
        answer = """
    Я запомнил выбор. Это ваша {n} игра
        """.format(n=12)

        bot.send_message(
                message.chat.id, 
                answer,
                reply_markup=markup
                        )




def launch_ratings(bot, message):
    markup = make_answer_buttons([
         'Выбрать режим',
         'Главное меню',
                                ])



    bot.send_message(
            message.chat.id, 
            """
            Лучшие книги по мнению наших игроков
            """,
            reply_markup=markup
                    )
       
def launch_personal_stat(bot, message):
    markup = make_answer_buttons([
         'Выбрать режим',
         'Главное меню',
                                ])



    bot.send_message(
            message.chat.id, 
            """
            Ваша статистика в игре:
            """,
            reply_markup=markup
                    )
       
def launch_leaderboard(bot, message):
    markup = make_answer_buttons([
         'Выбрать режим',
         'Главное меню',
                                ])




    bot.send_message(
            message.chat.id, 
            """
            Лучшие игроки на данный момент
            """,
            reply_markup=markup
                    )

def launch_404(bot, message):
    markup = make_answer_buttons([
         'Главное меню',
                                ])




    bot.send_message(
            message.chat.id, 
            """
К сожалению, что-то пошло не так: такой команды нет.
Возможно, произошла ошибка в самой игре. 
Возможно, вы использовали неожиданную текстовую команду.
Возвращайтесь в главное меню и попробуйте снова.
            """,
            reply_markup=markup
                    )







@bot.message_handler(commands=["start"])
def launch_main_menu(message):

    markup = make_answer_buttons([
         'Начать игру',
         'Посмотреть рейтинги книг',
         'Посмотреть список лучших игроков',
         'Посмотреть мою индивидуальную статистику',
                                ])
    
    # start session logging only on the start of session
    if (message.text.strip() == '/start'):
        make_event_log(message, 'session_start', '')

    bot.send_message(
        message.chat.id, 
        """
Давайте сыграем в игру!
Узнаем кое-что о ваших предпочтениях и о том, насколько они отличаются от других людей
        """,
        reply_markup=markup
                )

@bot.message_handler(content_types=["text"])
def handle_text(message):
    make_event_log(message, 'button_click', '{Button_name: '+ message.text.strip() +'}')

    if message.text.strip() in 'Начать игру':
        choise_category(bot, message)
    elif message.text.strip() == 'Посмотреть рейтинги книг':
        launch_ratings(bot, message)
    elif message.text.strip() == 'Посмотреть список лучших игроков':
        launch_leaderboard(bot, message)
    elif message.text.strip() == 'Посмотреть мою индивидуальную статистику':
        launch_personal_stat(bot, message)
    elif message.text.strip() == 'Главное меню':
        launch_main_menu(message)
    elif (message.text.strip() in topics_lst):
        # if it begining, we shold get new topic
        global topic
        topic = message.text
        topic = start_game(bot, message, topic)
    elif (message.text.strip() == 'Продолжить'):
        # if we are plaing, we should keep topic from last rounds
        start_game(bot, message, topic)
    elif message.text.strip() in ['Верхний', 'Нижний']:
        finish_game(bot, message)
    elif message.text.strip() in ['Пропустить']:
        skip_game(bot, message)

        
    else:
        launch_404(bot, message)









print('Ready for launch')
bot.polling(none_stop=True, interval=0)



