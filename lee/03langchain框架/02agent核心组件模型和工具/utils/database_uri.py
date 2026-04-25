

import os


def get_db_uri():
    username = os.environ["MYSQL_USERNAME"]
    password = os.environ["MYSQL_PASSWORD"]
    host = os.environ["MYSQL_HOST"]
    port = os.environ.get("MYSQL_PORT", "3306")
    database = os.environ["MYSQL_DATABASE"]
    return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"