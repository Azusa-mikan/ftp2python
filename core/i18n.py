# -*- coding: utf-8 -*-
"""
国际化支持模块

提供多语言日志消息和界面文本支持。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib


class I18n:
    """国际化支持类"""
    
    def __init__(self, language: str = 'zh'):
        """
        初始化国际化支持
        
        Args:
            language: 语言代码，支持 'zh_CN'（简体中文）和 'en_US'（英语）
        """
        self.language = self._normalize_language(language)
        self._messages = self._load_messages()
    
    def _normalize_language(self, language: str) -> str:
        """标准化语言代码"""
        lang_map = {
            'zh': 'zh_CN',
            'zh_cn': 'zh_CN',
            'zh-cn': 'zh_CN',
            'chinese': 'zh_CN',
            'en': 'en_US',
            'en_us': 'en_US',
            'en-us': 'en_US',
            'english': 'en_US'
        }
        return lang_map.get(language.lower(), 'zh_CN')
    
    def _load_messages(self) -> Dict[str, Dict[str, str]]:
        """从 TOML 文件加载多语言消息"""
        messages = {}
        locales_dir = Path(__file__).parent / 'locales'
        
        # 支持的语言列表
        supported_languages = ['zh_CN', 'en_US']
        
        for lang in supported_languages:
            locale_file = locales_dir / f'{lang}.toml'
            if locale_file.exists():
                try:
                    with open(locale_file, 'rb') as f:
                        locale_data = tomllib.load(f)
                    messages[lang] = self._flatten_dict(locale_data, sep='.')
                except Exception as e:
                    # 如果加载失败，使用空字典
                    logging.warning(f"Warning: Failed to load locale file {locale_file}: {e}")
                    messages[lang] = {}
            else:
                logging.warning(f"Warning: Locale file {locale_file} not found")
                messages[lang] = {}
        
        return messages
    
    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, str]:
        """将嵌套字典扁平化"""
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, str(v)))
        return dict(items)
    
    def get(self, key: str, **kwargs) -> str:
        """
        获取本地化消息
        
        Args:
            key: 消息键
            **kwargs: 格式化参数
            
        Returns:
            本地化后的消息
        """
        messages = self._messages.get(self.language, self._messages['zh_CN'])
        message = messages.get(key, key)
        
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError):
                return message
        return message
    
    def set_language(self, language: str) -> None:
        """
        设置语言
        
        Args:
            language: 语言代码
        """
        normalized_lang = self._normalize_language(language)
        if normalized_lang in self._messages:
            self.language = normalized_lang
    
    def get_available_languages(self) -> list:
        """
        获取可用语言列表
        
        Returns:
            可用语言代码列表
        """
        return list(self._messages.keys())


# 全局国际化实例
_i18n_instance = None


def _detect_system_language() -> str:
    """
    检测系统语言环境
    
    Returns:
        检测到的语言代码
    """
    import locale
    
    try:
        # 尝试获取系统默认语言
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            if system_locale.startswith('zh'):
                return 'zh_CN'
            elif system_locale.startswith('en'):
                return 'en_US'
    except:
        pass
    
    # 备用方案：检查环境变量
    for env_var in ['LANG', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES']:
        system_lang = os.environ.get(env_var, '').lower()
        if system_lang:
            if 'zh' in system_lang or 'cn' in system_lang:
                return 'zh_CN'
            elif 'en' in system_lang:
                return 'en_US'
    
    # Windows特定检测
    try:
        import ctypes
        windll = ctypes.windll.kernel32
        language_id = windll.GetUserDefaultUILanguage()
        # 中文语言ID范围
        if language_id in [0x0804, 0x0404, 0x0c04, 0x1004, 0x1404]:
            return 'zh_CN'
        # 英文语言ID
        elif language_id in [0x0409, 0x0809, 0x0c09, 0x1009, 0x1409, 0x1809, 0x1c09, 0x2009, 0x2409, 0x2809, 0x2c09, 0x3009, 0x3409]:
            return 'en_US'
    except:
        pass
    
    # 默认返回中文
    return 'zh_CN'


def init_i18n_from_config(config_data: Dict[str, Any] = None) -> None:
    """
    从配置数据初始化国际化设置
    
    Args:
        config_data: 配置数据字典，包含language字段
    """
    global _i18n_instance
    
    if config_data and 'language' in config_data:
        language = config_data['language']
        # 如果配置为auto，则自动检测系统语言
        if language.lower() == 'auto':
            language = _detect_system_language()
    else:
        # 自动检测系统语言
        language = _detect_system_language()
    
    # 标准化语言代码
    temp_i18n = I18n()
    normalized_lang = temp_i18n._normalize_language(language)
    
    if _i18n_instance is None or _i18n_instance.language != normalized_lang:
        _i18n_instance = I18n(normalized_lang)


def get_i18n(language: str = None) -> I18n:
    """
    获取国际化实例
    
    Args:
        language: 语言代码，如果为 None 则使用当前实例语言或系统默认语言
        
    Returns:
        国际化实例
    """
    global _i18n_instance
    
    if language is None:
        # 如果已有实例，直接返回当前实例
        if _i18n_instance is not None:
            return _i18n_instance
        
        # 否则自动检测系统语言
        system_lang = os.environ.get('LANG', '')
        if 'zh' in system_lang.lower() or 'cn' in system_lang.lower():
            language = 'zh_CN'
        else:
            language = 'en_US'
    
    # 标准化语言代码
    temp_i18n = I18n()
    normalized_lang = temp_i18n._normalize_language(language)
    
    if _i18n_instance is None or _i18n_instance.language != normalized_lang:
        _i18n_instance = I18n(normalized_lang)
    
    return _i18n_instance


def _(key: str, **kwargs) -> str:
    """
    快捷函数：获取本地化消息
    
    Args:
        key: 消息键
        **kwargs: 格式化参数
        
    Returns:
        本地化后的消息
    """
    return get_i18n().get(key, **kwargs)