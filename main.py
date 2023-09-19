import sqlalchemy
from sqlalchemy.sql.expression import text
import logging
from trove_emulation import models, sql_query

logging.basicConfig(format='[%(levelname)s]: %(message)s', encoding='utf-8', level=logging.INFO)

q = sql_query.Query()
q.columns = [
    'schema_name as name',
    'default_character_set_name as charset',
    'default_collation_name as collation',
]
q.tables = ['information_schema.schemata']
q.order = ['schema_name ASC']
t = text(str(q))

# маппинг <хост: версия>
mariadb_hosts = {
    'db1': '10.5',
    'db2': '10.6',
    'db3': '10.7',
}

for host, version in mariadb_hosts.items():
    host_info = f'{host} (v{version})'
    logging.info(f'Подключение к {host_info}...')
    engine = sqlalchemy.create_engine(f"mariadb+pymysql://user:password@{host}/mydatabase")
    client = engine.connect()
    logging.debug(f'Подключеное к {host_info}')
    database_names = client.execute(t)

    try:
        for count, database in enumerate(database_names):
            mysql_db = models.MySQLSchema(name=database[0],
                                            character_set=database[1],
                                            collate=database[2])
            next_marker = mysql_db.name
    except ValueError as e:
        logging.error(f'Ошибка с базой {host_info}: {str(e)}\n')
    else:
        logging.info(f'Все прошло без ошибок с базой {host_info}\n')
    
    client.close()