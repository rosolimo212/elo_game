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
    fresh_ratings_df = dl.get_data("""
        with 
        base as 
        (
            select item, rating, insert_time
            from tl.rating_history

            union all 

            select item_name as item, start_rating as rating, insert_time
            from tl.items
        ),
        fresh_note as
        (
            select *, max(insert_time) over (partition by item) as fresh_time
            from base
        )

        select item, rating
        from fresh_note
        where fresh_time = insert_time
                                """)
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

    battle1, battle2 = generate_pair(items)

    markup = make_answer_buttons([
         battle1,
         battle2,
         'Пропустить',
                                ])

    bot.send_message(
            message.chat.id, 
            """
            Выберете то, что вам нравится больше
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
    top_rating = dl.get_data("""
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

                limit 10
                """)
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

    score =  dl.get_data("""
                    with
                    random_rate_old as 
                    (
                        select 
                        user_id, avg(result) as random_value, count(distinct insert_time) as attempts
                        from tl.game_results
                        group by user_id
                    ), 
                    left_tbl as 
                    (
                        select battle1 as item, user_id, "user"
                            , case 
                                when result = 0 then 1
                                else 0
                            end as is_selected
                                --, row_number() as id
                        from tl.game_results
                    ),
                    right_tbl as 
                    (
                            select battle2 as item, user_id, "user"
                                        , case 
                                            when result = 1 then 1
                                            else 0
                                        end as is_selected
                        from tl.game_results
                    ),
                    pre_items as 
                    (
                        select * from left_tbl

                        union all

                        select * from right_tbl
                    ),
                    items as 
                    (
                        select *, row_number() over() as id
                        from pre_items
                    ),
                    global_stat as 
                    (
                        select item
                                    , sum(is_selected) as selected
                                    , count(is_selected) as total
                                    , sum(is_selected)::float / count(is_selected) as select_rate
                        from items
                        group by item
                    ),
                    personal_stat as 
                    (
                        select item, user_id, "user"
                                    , sum(is_selected) as selected
                                    , count(is_selected) as total
                                    , sum(is_selected)::float / count(is_selected) as select_rate
                        from items
                        group by item, user_id, "user"
                    ),
                    indiv_stat as 
                    (
                        select ps.*
                                , gs.select_rate as global_select_rate
                                , case 
                                    when (ps.select_rate <= 0.05) or (ps.select_rate >= 0.95) then 0
                                    else  round((100 * abs(gs.select_rate - ps.select_rate))::decimal, 0)
                                end as original_score
                        from personal_stat ps
                        left outer join global_stat gs on 
                            (ps.item=gs.item)
                    ),
                    original as 
                    (
                        select user_id, "user"
                                , avg(original_score) as original_score, sum(total) / 2 as attemps
                        from  indiv_stat
                        group by user_id, "user"
                    ),
                    random_rate as 
                    (
                        select user_id, "user"
                                , stddev_pop(select_rate)
                                ,  case 
                                    when stddev_pop(select_rate) <= 0.1 then 0
                                    when stddev_pop(select_rate) >= 0.9 then 100
                                    else round((100*(stddev_pop(select_rate)))::decimal,0)
                                end as non_random_rate
                        from personal_stat
                        group by user_id, "user"
                    )


                    select 
                            o."user"
                            , round(((o.attemps * o.original_score) + (o.attemps * (50 - non_random_rate))) / 100,1) as score
                            , round(o.attemps,0) as attemps 
                            , round(o.original_score,0) as original_score
                            , non_random_rate
                    from original o
                    left outer join random_rate rr on
                        (rr.user_id = o.user_id)
                    where o.user_id = {uid}

                    


                    """.format(
                        uid = user_id
                    ))
    favor =  dl.get_data("""
                    with
                    random_rate_old as 
                    (
                        select 
                        user_id, avg(result) as random_value, count(distinct insert_time) as attempts
                        from tl.game_results
                        group by user_id
                    ), 
                    left_tbl as 
                    (
                        select battle1 as item, user_id, "user"
                            , case 
                                when result = 0 then 1
                                else 0
                            end as is_selected
                                --, row_number() as id
                        from tl.game_results
                    ),
                    right_tbl as 
                    (
                            select battle2 as item, user_id, "user"
                                        , case 
                                            when result = 1 then 1
                                            else 0
                                        end as is_selected
                        from tl.game_results
                    ),
                    pre_items as 
                    (
                        select * from left_tbl

                        union all

                        select * from right_tbl
                    ),
                    items as 
                    (
                        select *, row_number() over() as id
                        from pre_items
                    ),
                    global_stat as 
                    (
                        select item
                                    , sum(is_selected) as selected
                                    , count(is_selected) as total
                                    , sum(is_selected)::float / count(is_selected) as select_rate
                        from items
                        group by item
                    ),
                    personal_stat as 
                    (
                        select item, user_id, "user"
                                    , sum(is_selected) as selected
                                    , count(is_selected) as total
                                    , sum(is_selected)::float / count(is_selected) as select_rate
                        from items
                        group by item, user_id, "user"
                    ),
                    indiv_stat as 
                    (
                        select ps.*
                                , gs.select_rate as global_select_rate
                                , case 
                                    when (ps.select_rate <= 0.05) or (ps.select_rate >= 0.95) then 0
                                    else  round((100 * abs(gs.select_rate - ps.select_rate))::decimal, 0)
                                end as original_score
                        from personal_stat ps
                        left outer join global_stat gs on 
                            (ps.item=gs.item)
                    ),
                    original as 
                    (
                        select user_id, "user"
                                , sum(original_score) as original_score, round(sum(total) / 2,0) as attemps
                        from  indiv_stat
                        group by user_id, "user"
                    ),
                    random_rate as 
                    (
                        select user_id, "user"
                                , stddev_pop(select_rate)
                                ,  case 
                                    when stddev_pop(select_rate) <= 0.1 then 0
                                    when stddev_pop(select_rate) >= 0.9 then 100
                                    else round((100*(stddev_pop(select_rate)))::decimal,0)
                                end as non_random_rate
                        from personal_stat
                        group by user_id, "user"
                    )


                    select *
                    from indiv_stat
                    where user_id = {uid} and total > 3

                    order by select_rate desc

                    limit 1

                    


                    """.format(
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
    lead_df = dl.get_data("""
                    with
                    random_rate_old as 
                    (
                        select 
                        user_id, avg(result) as random_value, count(distinct insert_time) as attempts
                        from tl.game_results
                        group by user_id
                    ), 
                    left_tbl as 
                    (
                        select battle1 as item, user_id, "user"
                            , case 
                                when result = 0 then 1
                                else 0
                            end as is_selected
                                --, row_number() as id
                        from tl.game_results
                    ),
                    right_tbl as 
                    (
                            select battle2 as item, user_id, "user"
                                        , case 
                                            when result = 1 then 1
                                            else 0
                                        end as is_selected
                        from tl.game_results
                    ),
                    pre_items as 
                    (
                        select * from left_tbl

                        union all

                        select * from right_tbl
                    ),
                    items as 
                    (
                        select *, row_number() over() as id
                        from pre_items
                    ),
                    global_stat as 
                    (
                        select item
                                    , sum(is_selected) as selected
                                    , count(is_selected) as total
                                    , sum(is_selected)::float / count(is_selected) as select_rate
                        from items
                        group by item
                    ),
                    personal_stat as 
                    (
                        select item, user_id, "user"
                                    , sum(is_selected) as selected
                                    , count(is_selected) as total
                                    , sum(is_selected)::float / count(is_selected) as select_rate
                        from items
                        group by item, user_id, "user"
                    ),
                    indiv_stat as 
                    (
                        select ps.*
                                , gs.select_rate as global_select_rate
                                , case 
                                    when (ps.select_rate <= 0.05) or (ps.select_rate >= 0.95) then 0
                                    else  round((100 * abs(gs.select_rate - ps.select_rate))::decimal, 0)
                                end as original_score
                        from personal_stat ps
                        left outer join global_stat gs on 
                            (ps.item=gs.item)
                    ),
                    original as 
                    (
                        select user_id, "user"
                                , avg(original_score) as original_score, sum(total) / 2 as attemps
                        from  indiv_stat
                        group by user_id, "user"
                    ),
                    random_rate as 
                    (
                        select user_id, "user"
                                , stddev_pop(select_rate)
                                ,  case 
                                    when stddev_pop(select_rate) <= 0.1 then 0
                                    when stddev_pop(select_rate) >= 0.9 then 100
                                    else round((100*(stddev_pop(select_rate)))::decimal,0)
                                end as non_random_rate
                        from personal_stat
                        group by user_id, "user"
                    )


                    select 
                            o."user"
                            , round(((o.attemps * o.original_score) + (o.attemps * (50 - non_random_rate))) / 100,1) as score
                            , round(o.attemps,0) as attemps 
                            , round(o.original_score,0) as original_score
                            , non_random_rate
                    from original o
                    left outer join random_rate rr on
                        (rr.user_id = o.user_id)
                    order by 2 desc

                    limit 10


                    """)
    lead_df.columns = ['Игрок', 'Счёт', 'Всего игр', 'Мера оригинальности', 'Мера неслучайности']
    print(lead_df)
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
    sending_alive_message(60 * 30)

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
        except:
            launch_404(bot, message)
    elif message.text.strip() in ['Пропустить']:
        skip_game(bot, message)
    else:
        launch_404(bot, message)




print('Ready for launch')
bot.polling(none_stop=True, interval=0)




