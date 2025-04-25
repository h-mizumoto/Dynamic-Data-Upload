import logging
import os
import psycopg2
import json
import boto3
import requests

from swagger_server import util
from swagger_server.utilities.manage_exception import ManageException
from requests.exceptions import Timeout
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

CONFIG_PATH = "/usr/src/app/swagger_server/configs/config.json"
CONFIG_KEY_MAX_COUNT = "max_count"
CONFIG_KEY_BUCKET_NAME = "bucket_name"
CONFIG_KEY_ENDPOINT_URL = "endpoint_url"

ENV_KEY_DB_HOST = "POSTGRES_HOST"
ENV_KEY_DB_PORT = "POSTGRES_PORT"
ENV_KEY_DB_NAME = "POSTGRES_DB"
ENV_KEY_DB_USER = "POSTGRES_USER"
ENV_KEY_DB_PASS = "POSTGRES_PASSWORD"

API_PREFIX = "/api/v1"
REPORT_API_PATH = API_PREFIX + '/report'
DEFAULT_MAX_COUNT = 10

NOTIFY_API_URL = 'http://notify:8080' + API_PREFIX + '/status'


# DB接続
def get_db_connection():
    """
     データベース接続関数
     環境変数を利用してPostgreSQLに接続する
    
    :return: DBコネクション
    
    """
    
    host = os.getenv(ENV_KEY_DB_HOST)
    port = os.getenv(ENV_KEY_DB_PORT)
    dbname = os.getenv(ENV_KEY_DB_NAME)
    user = os.getenv(ENV_KEY_DB_USER)
    password = os.getenv(ENV_KEY_DB_PASS)
    
    logger.debug("get_db_connection(): host : " + str(host))
    logger.debug("get_db_connection(): port : " + str(port))
    logger.debug("get_db_connection(): dbname : " + str(dbname))
    logger.debug("get_db_connection(): user : " + str(user))
    
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    except Exception as e:
        logger.exception("Dadtabase connection failed.")
        raise ManageException("Database connection error.", 500)
        
    return conn

# SQL実行
def execute_query(query, params) -> list:
    """
     データベースクエリ実行
    指定されたSQLクエリとパラメータを使用してPostgreSQLで実行しリスト形式で返す。
    
    :param query: 実行するSQLクエリ
    :type query: str
    :param params: パラメータ
    :type params: list or tuple

    :return: クエリの実行結果
    :rtype: list
    
    """
    results = []
    conn = get_db_connection()
    
    logger.debug("execute_query(): query : " + str(query))
    logger.debug("execute_query(): params: " + str(params))
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params) 
            results = cursor.fetchall()
            conn.commit()
    except Exception as e:
        conn.close()
        logger.exception("Database query execution failed.")
        raise ManageException("Database query execution failed.", 500)
        
    conn.close()
    
    logger.debug("execute_query(): results : " + str(results))
    
    return results
        

#設定ファイルの読み込み
def load_config():
    """
     CONFIG_PATHに設定された設定ファイルの読み込み
    
    :return: コンフィグ
    
    """
    try:
        with open(CONFIG_PATH, "r") as config_file:
            config = json.load(config_file)
    except Exception as e:
        logger.exception("Failed to load config file.")
        raise ManageException("Failed to load config file.", 500)

    logger.debug("load_config(): config" + str(config))
    return config

#立ち入り状態取得
def status_get_data(port, _datetime) -> list:
    """
    立入り状態の情報（テキストデータ）を取得する。

    :param port: ドローンポートのID
    :type port: str
    :param _datetime: 立入り検知の日時
    :type _datetime: str

    :rtype: list
    """
    logger.debug("status_get_data(): port:" + str(port))
    logger.debug("status_get_data(): _datetime:" + str(_datetime))
    
    config = load_config()
    max_count = DEFAULT_MAX_COUNT
    if CONFIG_KEY_MAX_COUNT in config:
        max_count = config[CONFIG_KEY_MAX_COUNT]
        
        # max_countが数値ではない場合のエラー
        if not isinstance(max_count, int) or max_count <= 0:
            logger.error("Invalid configuration.(max_count: " + str(max_count) + ")")
            raise ManageException("Invalid configuration.(max_count)", 400)
        
    # DBから立入り状態を取得し、レスポンスデータ作成
    query_status = """
            SELECT 
                ES.port, 
                ES.datetime, 
                ES.detect, 
                json_agg(json_build_object(
                    'id', EV.object_id,
                    'type', EV.object_type,
                    'detect', EV.detect,
                    'location', EV.location
                )) as event, 
                R.endpoint
            FROM ENTRY_STATUS_INFORMATION ES
            LEFT OUTER JOIN EVENT_INFORMATION EV 
                ON ES.ID = EV.ent_stat_id
            LEFT OUTER JOIN REPORT R
                ON ES.report_id = R.report_id
        """
    conditions = []
    params = []

    #port指定の場合
    if port:
        conditions.append("ES.port = %s ")
        params.append(port)

    #datetime指定の場合
    if _datetime:
        conditions.append("ES.datetime >= %s ")
        params.append(_datetime)
    
    if conditions:
        query_status += " WHERE " + " AND ".join(conditions)

    #GROUP句を設定    
    query_status += "GROUP BY ES.ID, EV.ent_stat_id, R.endpoint"
    #並び替えと最大件数
    query_status += " ORDER BY ES.datetime DESC LIMIT %s"
    params.append(max_count)

    results = execute_query(query_status, params)
    
    data = []
    for row in results:
        events = []
        if row[3] :
            events = row[3]
        data.append({
            "port": row[0],
            "datetime": row[1],
            "detect": row[2],
            "report_endpoint": row[4],
            "events": events
        })

    logger.debug("status_get_data(): data:" + str(data))
    return data

#立入り状態通知
def status_post_data(port, datetime, detect, events, report_id):
    """
    立入り状態通知

    :param port: ドローンポートのID
    :type port: str
    :param datetime: 立入り検知の日時
    :type datetime: str
    :param detect: 立入り状態の代表値
    :type datect: boolean
    :param events: 立入り検知の情報
    :type events: array
    :param report_id: レポートファイルの識別子 
    :type events: str
    
    """
    logger.debug("status_post_data(): port:" + port)
    logger.debug("status_post_data(): datetime:" + str(datetime))
    logger.debug("status_post_data(): detect:" + str(detect))
    logger.debug("status_post_data(): events:" + str(events))
    logger.debug("status_post_data(): report_id:" + str(report_id))


    report_endpoint = ""
    if report_id :
    # レポートIDとレポートエンドポイントの紐づけを解決
        query_report = """
            SELECT endpoint FROM REPORT WHERE report_id = %s
        """
        results = execute_query(query_report, (report_id,))

        if not results :
            logger.error("Not found report file. (Report ID: %s)", report_id)
            raise ManageException("Not found report file.", 404)
        else:
            report_row = results[0]
            report_endpoint = report_row[0]
    
    
    # レポートIDが空文字の場合は、SQLエラーとなるためNoneとする
    if not report_id:
        report_id = None
    
    # 立入り状態のDB登録
    query_status = """
        INSERT INTO ENTRY_STATUS_INFORMATION (port, datetime, detect, report_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    results = execute_query(query_status, (port, datetime, detect, report_id))
    result_row = results[0]
    entry_status_id = result_row[0]
    
    # 立入り状態（障害物の検知情報）のDB登録
    query_event = """
        INSERT INTO EVENT_INFORMATION (ent_stat_id, object_id, object_type, detect, location)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    for event in events:
        event_id = event.get('id')
        event_type = event.get('type')
        event_detect = event.get('detect')
        event_location = event.get('location', None)
        execute_query(query_event, (entry_status_id, event_id, event_type, event_detect, event_location))

    
    # 状態通知機能への通知
    notify(port, datetime, detect, events, report_endpoint)
    
    return 
 
# 状態通知機能のAPI実行  
def notify(port, datetime, detect, events, report_endpoint):
    """
    状態通知機能のAPIを実行

    :param port: ドローンポートのID
    :type port: str
    :param datetime: 立入り検知の日時
    :type datetime: str
    :param detect: 立入り状態の代表値
    :type datect: boolean
    :param events: 立入り検知の情報
    :type events: array
    :param report_endpoint: レポートファイルのエンドポイント
    :type events: str
    
    """
    
    logger.debug("notify(): port:" + port)
    logger.debug("notify(): datetime:" + str(datetime))
    logger.debug("notify(): detect:" + str(detect))
    logger.debug("notify(): events:" + str(events))
    logger.debug("notify(): report_endpoint:" + report_endpoint)

    notification_data = {
        "port": port,
        "datetime": str(datetime),
        "detect": detect,
        "event": events,
        "report_endpoint": report_endpoint
    }

    status_api_url = NOTIFY_API_URL
    params = notification_data
    
    try:
        response = requests.post(status_api_url, json=params)
    except Timeout:
        logger.exception("Timeout occured.")
        raise ManageException("Timeout occuered.", 500)
    except Exception as e:
        logger.exception("Error occuered.")
        raise ManageException("Error occuered.", 500)
        
    if response.status_code < 200 or 300 <= response.status_code:
        logger.error("notify request error. status code:" + str(response.status_code) + ", " + str(response.text))
        raise ManageException(str(response.text), response.status_code)
        
    logger.debug("notify(): response status:" + str(response.status_code))
    return 


def get_report(filename):
    """
     # 関数説明:
     レポート取得
     :param filename: レポートファイル名
     :type filename: str
    """
    
    logger.debug("get_report(): filename:" + str(filename))
    
    config = load_config()
    if CONFIG_KEY_BUCKET_NAME in config:
        bucket_name = config[CONFIG_KEY_BUCKET_NAME]
    else :
        logger.error("Failed to load config file. bucket_name parameter is invalid.")
        raise ManageException("Failed to load config file. bucket_name parameter is invalid.", 500)
    
    try:      
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucket_name)
        report_file = bucket.Object(filename).get()
        report_data = report_file["Body"].read()
    except s3.meta.client.exceptions.NoSuchKey as e:
        logger.exception("Not found report file.")
        raise ManageException("Not found report file.", 404)
    except Exception as e:
        logger.exception("Failed to get a report file.")
        raise ManageException("Failed to get a report file.", 500)
    
    # logger.debug("get_report(): report_data:" + str(report_data))

    return report_data
    

def put_report(report, filename) -> str:
    """
     # 関数説明:
     レポードアップロード
     :param report: 
     :type report: str
     :param filename: 
     :type filename: str
    """

    logger.debug("put_report(): report:" + str(report))
    logger.debug("put_report(): filename:" + str(filename))
    
    config = load_config()
    if CONFIG_KEY_BUCKET_NAME in config:
        bucket_name = config[CONFIG_KEY_BUCKET_NAME]
    else :
        logger.error("Failed to load config file. bucket_name parameter is invalid.")
        raise ManageException("Failed to load config file. bucket_name parameter is invalid.", 500)
        
    if CONFIG_KEY_ENDPOINT_URL in config:
        url = config[CONFIG_KEY_ENDPOINT_URL] 
        try:
            ret = urlparse(url)
        except Exception as e:
            logger.error("Failed to load config file. endpoint_url parameter is invalid.")
            raise ManageException("Failed to load config file. endpoint_url parameter is invalid.", 500)
    else :
        logger.error("Failed to load config file. endpoint_url parameter is invalid.")
        raise ManageException("Failed to load config file. endpoint_url parameter is invalid.", 500)
    
    try:      
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucket_name)
        bucket.upload_fileobj(report, filename)
    
    except Exception as e:
        logger.exception("Faild to upload a report file.")
        raise ManageException("Failed to upload a report file.", 500)

    report_endpoint = url + REPORT_API_PATH + "/" + filename
    
    query_insert = "INSERT INTO REPORT (endpoint) VALUES (%s) RETURNING report_id"
    report_tuple = (report_endpoint,)
    results = execute_query(query_insert, report_tuple)
    r = results[0]
    report_id = r[0]
    
    logger.debug("put_report(): report_id:" + str(report_id))

    return report_id
 
