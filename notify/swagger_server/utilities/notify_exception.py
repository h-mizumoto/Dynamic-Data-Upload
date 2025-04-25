# -*- coding: utf-8 -*-
import json


class NotifyException(Exception):
    """
    状態管理I/F用Exception
    エラーメッセージ、httpステータスコードを保持する。
    """

    def __init__(
            self,
            message: str,
            status_code: int = None):
        """
        Args:
            message str : メッセージ
            status_code int : ステータスコード
        """
        self.is_transparent = False
        self.error_message = message
        self.http_status_code = status_code
        
