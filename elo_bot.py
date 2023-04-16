# coding: utf-8
# ELO-bot main file
import telebot
from telebot import types

import pandas as pd
import numpy as np
import random

import matplotlib.pyplot as plt
from pylab import rcParams
import seaborn as sns

import schedule
import time

# module for working with SQL
import data_load as dl
settings = dl.read_yaml_config('config.yaml', section='telegram')

topics_dct = {
    'Популярные': 'is_popular', 
    'Книги про любовь': 'is_love',
    'Фантастика': 'is_fantastic',
    'Детективы': 'is_detective',
    'Классика': 'is_classic',
    'Антиутопии': 'is_anti',
    'Книги на русском': 'is_russian',
    'Книги на английском': 'is_english',
            }
topics_lst = list(topics_dct.keys())
topic = ''
battle1 = ''
battle2 = ''
bot = telebot.TeleBot(settings['token'])

# common functions
def data_frame_to_png(df, file_name):
    import matplotlib.pyplot as plt
    from pandas.plotting import table

    plot_df = df.copy()
    
    ax = plt.subplot(111, frame_on=False)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    plt.subplots_adjust(bottom=0.45, top=1)
    tbl = table(
        ax, 
        plot_df, 
        loc='center',
        rowLoc='left',
        colLoc='left',
        cellLoc='left'
    )
    tbl.set_fontsize(24)
    tbl.scale(3,4)
    plt.savefig(file_name+'.png', bbox_inches='tight')

def sending_alive_message(period_in_seconds):
    while True:
        bot.send_message(chat_id=249792088, text="Bot is stiil alive!")
        time.sleep(period_in_seconds)

# loggin functions
# event log
def make_event_log(message, event_name, params):
    user = message.from_user.username
    user_id = message.from_user.id

    log_lst = [user_id, user, event_name, params]
    log_df = pd.DataFrame([log_lst])
    log_df.columns = ['user_id', 'user_name', 'event_name', 'parameters']
    print(log_df)
    dl.insert_data(log_df, 'tl', 'events')

# battle log
def make_battle_log(message, battle1, battle2, result):
    user = message.from_user.username
    user_id = message.from_user.id

    for_data_load = [battle1, battle2, result, user, user_id]
    battle_df = pd.DataFrame([for_data_load], columns=['battle1', 'battle2', 'result', 'user', 'user_id'])
    print(battle_df)
    dl.insert_data(battle_df, 'tl', 'game_results')

# gaming functions
# return list of pair different items wihouhgt history
def generate_pair(items_list):
    battle1 = random.choice(items_list)
    battle2 = random.choice(items_list)
    if battle1 != battle2: 
        return [battle1, battle2]
    else:
        return generate_pair(items_list)

# return classic Elo propabilities
# elo_prob(2882, 2722) -> 0.7152 (72% chanses Carlsen (2882) to beat Wan Hao (2722))
def count_elo_prob(rw, rb):
    try:
        rw = float(rw)
        rb = float(rb)
        res = 1 / (1 + np.power(10, (rb-rw) / 400))
    except:
        0.5
    return res

# rating changing after game
# simple version
def count_elo_rating_changes(rating, opponent_rating, score):
    K = 20  
    expectation = count_elo_prob(rating, opponent_rating)
    new_rating = rating + K * (score - expectation)
    return np.round(new_rating,0)

def make_ratings(battle1, battle2, result):
    with open('make_rating.sql', 'r') as f:
        query = f.read()

    fresh_ratings_df =  dl.get_data(query)
    print(fresh_ratings_df[0:3])

    old_rating1 = fresh_ratings_df[fresh_ratings_df['item'] == battle1]['rating'].values[0]
    old_rating2 = fresh_ratings_df[fresh_ratings_df['item'] == battle2]['rating'].values[0]

    if result == 0:
        print(battle1, ' won')
        new_rating1 = count_elo_rating_changes(old_rating1, old_rating2, 1)
        new_rating2 = count_elo_rating_changes(old_rating1, old_rating2, 0)
    elif result == 1:
        print(battle2, ' won')
        new_rating1 = count_elo_rating_changes(old_rating1, old_rating2, 0)
        new_rating2 = count_elo_rating_changes(old_rating1, old_rating2, 1)
    else:
        print('Error')


    log_df = pd.DataFrame([[battle1, new_rating1], [battle2, new_rating2]])
    log_df.columns = ['item', 'rating']
    print(log_df)
    dl.insert_data(log_df, 'tl', 'rating_history')

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
            Выберите категорию
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

    battle1, battle2 = generate_pair(items)

    markup = make_answer_buttons([
         battle1,
         battle2,
         'Пропустить',
                                ])

    bot.send_message(
            message.chat.id, 
            """
            Выберите то, что вам нравится больше
            """,
            reply_markup=markup
                    )
    return topic, battle1, battle2
    
def skip_game(bot, message):
    markup = make_answer_buttons([
         'Продолжить',
         'Посмотреть мою индивидуальную статистику',
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
    
def finish_game(bot, message, battle1, battle2, result):
    make_ratings(battle1, battle2, result)
    make_battle_log(message, battle1, battle2, result)
    markup = make_answer_buttons([
        'Продолжить',
        'Посмотреть мою индивидуальную статистику',
        'Главное меню',
                                ])
    answer = """
👍
    """

    bot.send_message(
            message.chat.id, 
            answer,
            reply_markup=markup
                    )

def launch_ratings(bot, message):
    with open('top_rating.sql', 'r') as f:
        query = f.read()
    top_rating = dl.get_data(query)

    rcParams['figure.figsize'] = 12, 9
    fig = plt.figure()
    fig = sns.heatmap(
            top_rating.set_index('item'), 
            cmap="RdYlGn", 
            annot=True,
            fmt=".0f",
            center=1600,
            vmin=1500, vmax=1700,
            cbar=False,
            square=True,
            ).figure.savefig("hm.png")
    
    markup = make_answer_buttons([
         'Главное меню',
                                ])

    bot.send_message(
            message.chat.id, 
            """
Лучшие книги по мнению наших игроков.
Чем больше число (рейтинг), тем чаще игроки выбирали эту книгу
            """,
            reply_markup=markup
                    )
    
    file = open('hm.png', 'rb')
    bot.send_photo(message.chat.id, file, reply_markup=markup)
       
def launch_personal_stat(bot, message):
    user = message.from_user.username
    user_id = message.from_user.id

    with open('score.sql', 'r') as f:
        query = f.read()
    score =  dl.get_data(query.format(
                        uid = user_id
                    ))
    with open('favor.sql', 'r') as f:
        query = f.read()
    favor =  dl.get_data(query.format(
                        uid = user_id
                    ))

    try:
        answer = """
    Ваша статистика в игре:
        сыграно "боёв" - {games}
        общий счёт - {score}
        мера оригинальности (чем больше, тем орининальнее) - {original_score}
        мера неслучайности (чем больше, тем достоверней) - {non_random_score}
        любимая книга - {book}
        """.format(
            games = score['attemps'].values[0],
            score = score['score'].values[0],
            original_score = score['original_score'].values[0],
            non_random_score = score['non_random_rate'].values[0],
            book = favor['item'].values[0]
        )
    except:
        answer = "Ваша статистика в данный момент недоступна"

    markup = make_answer_buttons([
            'Главное меню',
                                    ])

    bot.send_message(
            message.chat.id, 
            answer,
            reply_markup=markup
                    )
       
def launch_leaderboard(bot, message):
    with open('leaderboard.sql', 'r') as f:
        query = f.read()

    lead_df = dl.get_data(query)
    lead_df.columns = ['Игрок', 'Счёт', 'Всего игр', 'Мера оригинальности', 'Мера неслучайности']

    for col in lead_df.columns[1:]:
        lead_df[col] = lead_df[col].astype('int')

    import matplotlib.pyplot as plt
    fig_ax= plt.figure()
    fig_ax = sns.heatmap(
            lead_df.set_index('Игрок'), 
            cmap="RdYlGn", 
            annot=True,
            fmt=".0f",
            # center=1600,
            vmin=-15000, vmax=17000,
            cbar=False,
            square=True,
            )
    fig_ax.set(xlabel="", ylabel="")
    fig_ax.xaxis.tick_top()
    plt.xticks(rotation=5)
    fig_ax.figure.savefig("leaderboard.png")
    
    
    markup = make_answer_buttons([
         'Главное меню',
                                ])

    bot.send_message(
            message.chat.id, 
            """
    Лучшие игроки на данный момент.
    Мера оригинальности (чем больше, тем орининальнее) - насколько ваши вкусы отличаются от среднестатистических
    Мера неслучайности (чем больше, тем достоверней) - велика ли вероятность получить такие же результаты, 
как и вас, нажимая случайные кнопки
            """,
            reply_markup=markup
                    )
    file = open('leaderboard.png', 'rb')
    bot.send_photo(message.chat.id, file, reply_markup=markup)

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
Если проблема повторяется, нажмите /start
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
    # sending_alive_message(60 * 30)

@bot.message_handler(content_types=["text"])
def handle_text(message):
    make_event_log(message, 'button_click', '{Button_name: '+ message.text.strip() +'}')

    if message.text.strip() in 'Начать игру':
        try:
            choise_category(bot, message) 
        except:
            launch_404(bot, message)
    elif message.text.strip() == 'Посмотреть рейтинги книг':
        try:
            launch_ratings(bot, message)
        except:
            launch_404(bot, message)
    elif message.text.strip() == 'Посмотреть список лучших игроков':
        try:
            launch_leaderboard(bot, message)
        except:
            launch_404(bot, message)
    elif message.text.strip() == 'Посмотреть мою индивидуальную статистику':
        try:
            launch_personal_stat(bot, message)
        except:
            launch_404(bot, message)
    elif message.text.strip() == 'Главное меню':
        try:
            launch_main_menu(message)
        except:
            launch_404(bot, message)
    elif (message.text.strip() in topics_lst):
        # if it begining, we shold get new topic
        global topic
        global battle1
        global battle2
        topic = message.text
        try:
            topic, battle1, battle2 = start_game(bot, message, topic)
        except:
            launch_404(bot, message)
    elif (message.text.strip() == 'Продолжить'):
        try:
            # if we are plaing, we should keep topic from last rounds
            topic, battle1, battle2 = start_game(bot, message, topic)
        except:
            launch_404(bot, message)
    elif message.text.strip() in [battle1, battle2]:
        try:
            if (message.text.strip() == battle1):
                result = 0
            elif (message.text.strip() == battle2):
                result = 1
            else:
                result = -1
            finish_game(bot, message, battle1, battle2, result)
        except Exception as e:
            print(str(e))
            launch_404(bot, message)
    elif message.text.strip() in ['Пропустить']:
        skip_game(bot, message)
    else:
        try:
            launch_404(bot, message)
        except:
            bot.send_message(chat_id=249792088, text="Опять какая-то хрень")

bot.polling(none_stop=True, interval=0)