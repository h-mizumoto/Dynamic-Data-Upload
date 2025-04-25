import logging
from flask import make_response # type: ignore
from swagger_server.service import service

logger = logging.getLogger(__name__)

def status_post(body):  # noqa: E501
    """立入り状態通知API

    立入り状態の情報（テキストデータ）を通知するためのAPI # noqa: E501

    :param body: 通知データ
    :type body: dict | bytes

    :rtype: None
    """
    logger.debug("status_post(): body : " + str(body))

    # リクエストデータ処理
    dronePortId = body.get('port')
    timestamp = body.get('datetime')
    anyDetection = body.get('detect')
    events = body.get('event')
    reportEndpointUrl= body.get('report_endpoint')

    service.notify_local_data(dronePortId, timestamp, anyDetection, events, reportEndpointUrl)

    response = make_response('', 200)
    
    logger.debug("status_post(): response status code : " + str(response.status_code))
    logger.debug("status_post(): response headers : " + str(response.headers))
    
    return response