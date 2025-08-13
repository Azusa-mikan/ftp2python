# -*- coding: utf-8 -*-

import logging
from typing import Optional

from .i18n import get_i18n, _


def setup_logging(level: int = logging.INFO, format_string: Optional[str] = None, language: str = None) -> None:
    """
    配置日志系统
    
    Args:
        level: 日志级别
        format_string: 自定义日志格式
        language: 语言代码（zh_CN 或 en_US）
    """
    if format_string is None:
        format_string = '%(asctime)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True  # 强制重新配置，覆盖之前的配置
    )
    
    # 禁用 pyftpdlib 的详细日志输出
    logging.getLogger('pyftpdlib').setLevel(logging.ERROR)
    
    # 设置国际化语言
    if language:
        get_i18n(language)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(name)


class I18nLogger:
    """
    支持国际化的日志记录器包装类
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def info(self, key: str, **kwargs) -> None:
        """记录信息级别日志"""
        self.logger.info(get_i18n().get(key, **kwargs))
    
    def warning(self, key: str, **kwargs) -> None:
        """记录警告级别日志"""
        self.logger.warning(get_i18n().get(key, **kwargs))
    
    def error(self, key: str, **kwargs) -> None:
        """记录错误级别日志"""
        self.logger.error(get_i18n().get(key, **kwargs))
    
    def debug(self, key: str, **kwargs) -> None:
        """记录调试级别日志"""
        self.logger.debug(get_i18n().get(key, **kwargs))
    
    def critical(self, key: str, **kwargs) -> None:
        """记录严重错误级别日志"""
        self.logger.critical(get_i18n().get(key, **kwargs))


def get_i18n_logger(name: str) -> I18nLogger:
    """
    获取支持国际化的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        支持国际化的日志记录器
    """
    return I18nLogger(get_logger(name))