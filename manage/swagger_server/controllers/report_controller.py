import logging
import connexion
import six
import mimetypes

from flask import make_response
from swagger_server.service.service import get_report, put_report
from swagger_server.models.error_response import ErrorResponse  # noqa: E501
from swagger_server.models.report_upload_response import ReportUploadResponse  # noqa: E501
from swagger_server import util

logger = logging.getLogger(__name__)


def report_get(filename):  # noqa: E501
    """レポート取得API

    立入り状態のレポートファイルをダウンロードするためのAPI # noqa: E501

    :param filename: レポートファイル名
    :type filename: str

    :rtype: None
    """
    logger.info("Get Report API start.")

    logger.debug("report_get(): filename : " + str(filename))
    
    report = get_report(filename)
    
    response = make_response(report, 200)
    mtype = mimetypes.guess_type(filename)
    if mtype[0] :
        ctype = mtype[0]
    else :
        ctype = "application/octet-stream"
    response.headers["Content-Type"] = ctype

    if 'Server' in response.headers:
        del response.headers['Server']

    if 'Date' in response.headers:
        del response.headers['Date']

    if 'Transfer-Encoding' in response.headers:
        del response.headers['Transfer-Encoding']

    logger.debug("report_get(): response status code : " + str(response.status_code))
    logger.debug("report_get(): response headers : " + str(response.headers))
    
    logger.info("Get Report API end.")
    return response


def report_post(report, filename):  # noqa: E501
    """レポートアップロードAPI

    立入り状態のレポートファイルをアップロードするためのAPI # noqa: E501

    :param report: 
    :type report: str
    :param filename: アップロードするレポートのファイル名
    :type filename: str

    :rtype: ReportUploadResponse
    """
    logger.info("Post Report API start.")

    logger.debug("report_post(): report : " + str(report))
    logger.debug("report_post(): filename : " + str(filename))
    
    report_id = put_report(report, filename)
    body = {"report_id": report_id}
    
    response = make_response(body, 200)

    if 'Server' in response.headers:
        del response.headers['Server']

    if 'Date' in response.headers:
        del response.headers['Date']

    if 'Transfer-Encoding' in response.headers:
        del response.headers['Transfer-Encoding']

    logger.debug("report_post(): response status code : " + str(response.status_code))
    logger.debug("report_post(): response headers : " + str(response.headers))
    
    logger.info("Post Report API end.")
    return response

