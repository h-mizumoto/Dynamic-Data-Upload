import logging
from swagger_server import util
from flask import jsonify, make_response # type: ignore
from swagger_server.utilities.manage_exception import ManageException
from swagger_server.service import service
from connexion import request

logger = logging.getLogger(__name__)

# 立入り状態取得
def status_get(port=None, _datetime=None):  # noqa: E501
    """立入り状態取得API

    立入り状態の情報（テキストデータ）を取得するためのAPI。立ち入り状態を最大10件返却する。 # noqa: E501

    :param port: ドローンポートのID。指定したドローンポートの立ち入り状態を返却する。
    :type port: str
    :param _datetime: 立ち入り検知の日時。指定した日時より新しいデータを返す。
    :type _datetime: str

    :rtype: List[StatusResponse]
    """
    logger.info("Get Status API start.")

    # クエリパラメタの datetimeは予約語であるため_datetimeに設定する
    _datetime = request.args.get('datetime', None)

    logger.debug("status_get(): port : " + str(port))
    logger.debug("status_get(): _datetime : " + str(_datetime))

    if _datetime:
        try:
            _datetime = util.deserialize_datetime(_datetime)
        except ValueError as e:
            logger.exception("Invalid datetime format.")
            raise ManageException("Invalid datetime format.", 400)
    
    status = service.status_get_data(port, _datetime)
    
    response = make_response(jsonify(status))

    if 'Server' in response.headers:
        del response.headers['Server']

    if 'Date' in response.headers:
        del response.headers['Date']

    if 'Transfer-Encoding' in response.headers:
        del response.headers['Transfer-Encoding']

    logger.debug("status_get(): response status code : " + str(response.status_code))
    logger.debug("status_get(): response headers : " + str(response.headers))
    logger.debug("statur_get(): response data : " + str(response.data))

    logger.info("Get Status API end.")
    return response


def status_post(body):  # noqa: E501
    """立入り状態通知API

    立入り状態の情報（テキストデータ）を通知するためのAPI # noqa: E501

    :param body: 通知データ
    :type body: dict | bytes

    :rtype: None
    """
    logger.info("Post Status API start.") 

    logger.debug("status_post(): body : " + str(body))

    # リクエストデータ処理
    port = body.get('port')
    datetime = body.get('datetime')
    detect = body.get('detect')
    events = body.get('event')
    report_id= body.get('report_id')

    try:
        _datetime = util.deserialize_datetime(datetime)
    except ValueError as e:
        logger.exception("Invalid datetime format.")
        raise ManageException("Invalid datetime format.", 400)
    
    service.status_post_data(port, _datetime, detect, events, report_id)

    response = make_response('', 204)
    
    if 'Server' in response.headers:
        del response.headers['Server']

    if 'Date' in response.headers:
        del response.headers['Date']

    if 'Transfer-Encoding' in response.headers:
        del response.headers['Transfer-Encoding']

    logger.debug("status_post(): response status code : " + str(response.status_code))
    logger.debug("status_post(): response headers : " + str(response.headers))

    logger.info("Post Status API end.")
    return response

