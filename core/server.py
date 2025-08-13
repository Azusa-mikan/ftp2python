# -*- coding: utf-8 -*-
"""FTP 服务器核心模块

提供 FTP 处理器选项应用功能。
用户管理功能已移至 user_manager.py 模块。
配置管理功能已移至 config.py 模块。
服务器管理功能已移至 server_manager.py 模块。
"""

import logging
from typing import Dict, Any
from .i18n import _
from .logger import get_i18n_logger

def apply_handler_options(handler, config: Dict[str, Any]) -> None:
    """
    应用处理器选项
    
    Args:
        handler: FTP 处理器类
        config: 配置字典
    """
    logger = get_i18n_logger(__name__)
    
    # 被动模式端口范围
    passive_ports = config.get("passive_ports")
    if passive_ports:
        try:
            if isinstance(passive_ports, str):
                start, end = map(int, passive_ports.split("-"))
            elif isinstance(passive_ports, list) and len(passive_ports) == 2:
                start, end = int(passive_ports[0]), int(passive_ports[1])
            else:
                raise ValueError(_("passive_ports_format_invalid", passive_ports=passive_ports))
            
            if start > end or start < 1024 or end > 65535:
                raise ValueError(_("passive_ports_range_invalid", start=start, end=end))
                
            handler.passive_ports = range(start, end + 1)
            logger.info("network_passive_ports", start=start, end=end)
        except (ValueError, TypeError) as e:
            logger.error("passive_ports_format_invalid", passive_ports=passive_ports)
    
    # 横幅消息
    banner = config.get("banner")
    if banner:
        handler.banner = str(banner)
        logger.info("network_banner_message", banner=banner)
    
    # 最大连接数
    max_cons = config.get("max_cons")
    if max_cons:
        try:
            handler.max_cons = int(max_cons)
            logger.info("network_max_connections", max_cons=max_cons)
        except (ValueError, TypeError):
            logger.error("max_cons_invalid", max_cons=max_cons)
    
    # 每个IP最大连接数
    max_cons_per_ip = config.get("max_cons_per_ip")
    if max_cons_per_ip:
        try:
            handler.max_cons_per_ip = int(max_cons_per_ip)
            logger.info("network_max_connections_per_ip", max_cons_per_ip=max_cons_per_ip)
        except (ValueError, TypeError):
            logger.error("max_cons_per_ip_invalid", max_cons_per_ip=max_cons_per_ip)