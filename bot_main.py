import pandas as pd
import numpy as np
import random

import telebot
from telebot import types
import requests

import yaml, json, boto3, botocore
import psycopg2 as ps

import data_load as dl

settings = dl.read_yaml_config('config.yaml', section='telegram')
global battle1
global battle2
global book_dct 

book_list = [
    'Мастер и Маргарита',
    'Преступление и наказание',
    'Ромео и Джульета',
    'Незнайка на Луне',
    'Гарри Поттер и философский камень',
    'Властелин Колец',
    'Айвенго',
    'Вокруг света за 80 дней',
    'Три повести о Малыше и Карлсоне',
    'Дядя Фёдор, пёс и кот',
]


# return classic Elo propabilities
# elo_prob(2882, 2722) -> 0.7152 (72% chanses Carlsen (2882) to beat Wan Hao (2722))
def elo_prob(rw, rb):
    try:
        rw=float(rw)
        rb=float(rb)
        res=1/(1+np.power(10, (rb-rw)/400))
    except:
        0.5
    return res

# rating changing after game
# elo_rating_changes(1600, 1200, 0.5)
def elo_rating_changes(rating, opponent_rating, score):
    K = 20  
    expectation=elo_prob(rating, opponent_rating)
    new_rating=rating+K*(score-expectation)
    return np.round(new_rating,0)

def generate_pair(book_list):
    battle1 = random.choice(book_list)
    battle2 = random.choice(book_list)
    if battle1 != battle2: 
        return [battle1, battle2]
    else:
        return generate_pair(book_list)

def generate_result():
    return random.choice([0,1])

def get_battle_results(battle1, battle2, result, book_dct):
    if result == 0:
        print(battle1, 'won')
        new_rating1 = elo_rating_changes(book_dct[battle1], book_dct[battle2], 1)
        new_rating2 = elo_rating_changes(book_dct[battle2], book_dct[battle1], 0)
    elif result == 1:
        print(battle2, 'won')
        new_rating1 = elo_rating_changes(book_dct[battle1], book_dct[battle2], 0)
        new_rating2 = elo_rating_changes(book_dct[battle2], book_dct[battle1], 1)
    else:
        print('Error')
        
    book_dct.update({battle1:new_rating1})
    book_dct.update({battle2:new_rating2})
    
    return book_dct

def get_df_from_dict(book_dct):
    import pandas as pd
    df = pd.DataFrame.from_dict(book_dct, orient='index').reset_index()
    df.columns = ['item', 'rating']
    df['rating'] = df['rating'].astype('int')
    df = df.sort_values(by='rating', ascending=False)
    
    return df

def data_frame_to_png(df, file_name):
    import matplotlib.pyplot as plt
    from pandas.plotting import table
    
    ax = plt.subplot(111, frame_on=False)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    plt.subplots_adjust(bottom=0.45, top=1)
    t_channels = table(
        ax, 
        df, 
        loc='center',
        rowLoc='left',
        colLoc='left',
        cellLoc='left'
    )
    t_channels.set_fontsize(24)
    t_channels.scale(3,4)
    plt.savefig(file_name+'.png', bbox_inches='tight')
    

# start_rating = 1600
# ratings = np.ones(len(book_list)) * start_rating
# book_dct = dict(zip(book_list, ratings))


def make_button(button_name, markup):
    item=types.KeyboardButton(button_name)
    markup.add(item)
    
    return markup 

bot = telebot.TeleBot(settings['token'])
@bot.message_handler(commands=["start"])
def start_menu(message):
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup = make_button('New game', markup)
    markup = make_button('Show all ratings', markup)
    
    bot.send_message(
        message.chat.id, 
        """
        Hi! Lets' play a game?
        """,
        reply_markup=markup
                )
def new_game(message):
    global battle1
    global battle2
    battle1, battle2 = generate_pair(book_list)
    
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup = make_button(battle1, markup)
    markup = make_button(battle2, markup)
    markup = make_button('Main menu', markup)
    
    bot.send_message(
        message.chat.id, 
        """
        What is better for you?
        """,
        reply_markup=markup
                )
    
def show_ratings(message, book_dct):
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup = make_button('Main menu', markup)
    
    df = get_df_from_dict(book_dct)
    data_frame_to_png(df, 'results')
    
    file = open('results.png', 'rb')
    
    bot.send_photo(message.chat.id, file, reply_markup=markup)

def show_pair_results(message):
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup = make_button('Main menu', markup)
    
    bot.send_message(
        message.chat.id, 
        """
        Results will by soon
        """,
        reply_markup=markup
                )
    
@bot.message_handler(content_types=["text"])
def handle_text(message):
    global battle1
    global battle2
    global book_dct

    rating_df = dl.get_data("""
                with 
                base as 
                (
                    select item, rating, insert_time, max(insert_time) over (partition by item) as fresh_time
                    from tl.rating_history
                )
                select item, rating
                from base
                where fresh_time = insert_time
                """)

    result = -1
    if message.text.strip() == 'New game':
        new_game(message)
    elif message.text.strip() == 'Show all ratings':
        show_ratings(message, book_dct)
    elif message.text.strip() == 'Main menu':
        start_menu(message)
    elif message.text.strip() == 'Continue':
        new_game(message)
    elif message.text.strip() == battle1:
        result = 0
    elif message.text.strip() == battle2:
        result = 1
    if result >= 0:
        book_dct = dict(zip(rating_df['item'].values, rating_df['rating'].values))
        book_dct = get_battle_results(battle1, battle2, result, book_dct)
        rating_df = get_df_from_dict(book_dct)
        to_base_df = rating_df[rating_df['item'].isin([battle1, battle2])]
        dl.insert_data(to_base_df, 'tl', 'rating_history')

        markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup = make_button('Continue', markup)
        markup = make_button('Show all ratings', markup)
        markup = make_button('Main menu', markup)
        
        bot.send_message(
            message.chat.id, 
            ("""
            Good choice!
            New ratings:
            """ + battle1 + ' ' + str(book_dct[battle1]) + '\n'
                + battle2 + ' ' + str(book_dct[battle2]) + '\n')
            ,
            reply_markup=markup
                    )
        user = message.from_user.username
        user_id = message.from_user.id

        for_data_load = [battle1, battle2, result, user, user_id]
        r_df = pd.DataFrame([for_data_load], columns=['battle1', 'battle2', 'result', 'user', 'user_id'])
        dl.insert_data(r_df, 'tl', 'game_results')
        
bot.polling(none_stop=True, interval=0)


