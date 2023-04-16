# -*- coding: utf-8 -*-
import sys, logging

# наше всё
import numpy as np
import pandas as pd

# настройки pandas, с которыми лучше почти всегда
pd.set_option('display.max_rows', 45000)
pd.set_option('display.max_columns', 50000)
pd.set_option('display.max_colwidth', 5000)


current_yaml='config.yaml'


logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', \
                    datefmt='%Y-%m-%d %H:%M:%S', filemode='w', level=logging.INFO)

try:
    import yaml, json, boto3, botocore
    import psycopg2 as ps
    import pandas as pd
    import numpy as np
#     from __future__ import print_function
except ImportError as err:
    sys.stderr.write(f"Error {err} occured in module {__name__} file: {__file__}")
    sys.exit(1)


def test():
    print('Data load working')


def read_yaml_config(yaml_file: str, section: str) -> dict:
    with open(yaml_file, 'r') as yaml_stream:
        descriptor = yaml.full_load(yaml_stream)
        if section in descriptor:
            configuration = descriptor[section]
            return configuration
        else:
            logging.error(f"Section {section} not find in the file '{yaml_file}'")
            sys.exit(1)


def get_data(query: str, file=current_yaml, section='postgres_local') -> list:
    settings = read_yaml_config(file, section)
    conn = None
    try:
        conn = ps.connect(**settings)
        cur = conn.cursor()
        cur.execute(query)
        try:
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            df = pd.DataFrame(rows, columns=colnames)
        except:
            df=pd.DataFrame()
        cur.close()
        conn.close()
        return df
    except (Exception, ps.DatabaseError) as err:
        logging.error(f"PostgreSQL can't execute query - {err}")
    finally:
        if conn is not None:
            conn.close()
            


def read_text_file(text_file: str) -> list:
    lines = []
    with open(text_file, 'r') as df:
        for line in df:
            line = line.replace("\n", "")
            lines.append(line)
    return lines



def get_engine(file, section='postgres_local'):
    settings = read_yaml_config(file, section)
    from sqlalchemy import create_engine
    postgresql_engine_st = "postgresql://"+settings['user']+":"+settings['password']+"@"+settings['host']+"/"+settings['database']
    postgresql_engine = create_engine(postgresql_engine_st)

    return postgresql_engine

def insert_data(df_to_sql, schema, table_name):
    import datetime
    now = datetime.datetime.now()

    main_engine=get_engine('config.yaml')

    df_to_sql['insert_time'] = now
    df_to_sql.to_sql(
                            table_name, 
                            con=main_engine, 
                            schema=schema,
                            if_exists='append', 
                            index=False
                        )
    print(str(len(df_to_sql))+' rows inserted to  '+table_name)

