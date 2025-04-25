import logging
import requests # type: ignore
import json
from swagger_server.utilities.notify_exception import NotifyException
from requests.exceptions import Timeout
from flask import make_response

logger = logging.getLogger(__name__)

CONFIG_PATH = "/usr/src/app/swagger_server/configs/config.json"
CONFIG_LOCAL_URL = "local_url"
CONFIG_LOCAL_API_KEY = "local_api_key"

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
        raise NotifyException("Failed to load config file.", 500)

    logger.debug("load_config(): config" + str(config))
    return config

#ローカルデータ管理に通知
def notify_local_data(dronePortId, timestamp, anyDetection, events, reportEndpointUrl):
    """
    ローカルデータ管理に通知。

    :param dronePortId: ドローンポートのID
    :param timestamp: 日時
    :param anyDetection: 検知フラグ
    :param events: イベントのリスト
    :param reportEndpointUrl: レポートのエンドポイント
    """

    logger.debug("notify_local_data(): dronePortId:" + dronePortId)
    logger.debug("notify_local_data(): timestamp:" + str(timestamp))
    logger.debug("notify_local_data(): anyDetection:" + str(anyDetection))
    logger.debug("notify_local_data(): events:" + str(events))
    logger.debug("notify_local_data(): reportEndpointUrl:" + str(reportEndpointUrl))

    event_list = []
    #リストからjsonを取り出す
    for ev in events:        
        tmp = {}
        #locationの値(緯度経度)を分割
        if 'location' in ev:
            location_div = ev['location'].split(",")         
            #分割した値のデータ型を変更し、変数に設定
            try:
                latitude = float(location_div[0])
                longitude = float(location_div[1])
                ev['location'] = {
                    "latitude": latitude,
                    "longitude": longitude
                }
                tmp['location'] = ev['location']
            except ValueError:
                logger.warn("location value is not valid format.")  
            except Exception as e:
                logger.warn("location value is not valid format.")
    
                ev['location'] = {"latitude": latitude,
                                  "longitude": longitude  
                                 }
                tmp['location'] = ev['location']
        
        tmp['objectId'] = ev['id']
        tmp['objectType'] = ev['type']
        tmp['detectionStatus'] = ev['detect']
        
        #リストに追加
        event_list.append(tmp)

    notification_data = {
        "dronePortId": dronePortId,
        "timestamp": timestamp,
        "anyDetection": anyDetection,
        "events": event_list,
        "reportEndpointUrl": reportEndpointUrl
    }
    
    # 設定ファイルからローカルデータ管理の接続情報を取得
    config = load_config()
    if CONFIG_LOCAL_URL in config and config[CONFIG_LOCAL_URL] :
        local_url = config[CONFIG_LOCAL_URL]
    else:
        logger.error("Not found local_url. (Local URL: %s)", CONFIG_LOCAL_URL)
        raise NotifyException("Not found local_url.", 500)
    
    if CONFIG_LOCAL_API_KEY in config and config[CONFIG_LOCAL_API_KEY] :
        local_api_key = config[CONFIG_LOCAL_API_KEY]
    else:
        logger.error("Not found local_api_key. (Local API Key: %s)", CONFIG_LOCAL_API_KEY)
        raise NotifyException("Not found local_api_key.", 500)

    # ローカルデータ管理へ状態通知
    try:
        logger.debug("notify_local_data(): local_url:" + local_url)
        logger.debug("notify_local_data(): notification_data:" + str(notification_data))
        response = requests.post(
            local_url,
            json=notification_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": local_api_key
            }
        )    
    except Timeout:
        logger.exception("Timeout occured.")
        raise NotifyException("Timeout occuered.", 500)
    except Exception as e:
        logger.exception("Error occuered.")
        raise NotifyException("Error occuered.", 500)
        
    if response.status_code < 200 or 300 <= response.status_code:
        logger.error("notify request error. status code:" + str(response.status_code) + ", " + str(response.text))
        raise NotifyException(str(response.text), response.status_code)
        
    logger.debug("notify(): response status:" + str(response.status_code))
    return
