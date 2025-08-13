# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from typing import Dict, Any

from .i18n import _

try:
    import tomllib
except ImportError:
    import tomli as tomllib


DEFAULT_CONFIG_NAME = "config.toml"
DEFAULT_SHARED_DIR = "shared"

# 默认配置模板
DEFAULT_CONFIG_TEMPLATE = '''# FTP 服务器配置文件

# 服务器设置
port = 2121
listen = "0.0.0.0"

# 连接限制
max_cons = 256
max_cons_per_ip = 10

# 被动模式端口范围（可选）
# passive_ports = [50000, 50100]

# 欢迎语（可选）
banner = "欢迎使用 FTP 服务器"

# 用户配置
[[users]]
username = "user"
password = "123456"
perm = "elradfmw" # 权限配置: e 进入目录 l 列出内容 r 读取 a 追加 d 删除 f 重命名 m 创建目录 w 写入
# home = "./data/user"  # 可选，不指定则使用共享目录
'''


def load_toml_bytes(b: bytes) -> Dict[str, Any]:
    """加载 TOML 字节数据"""
    return tomllib.loads(b.decode("utf-8"))


def create_default_config(cfg_path: Path) -> None:
    """创建默认配置文件"""
    try:
        cfg_path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding='utf-8')
        logging.info(_("config_created", path=str(cfg_path)))
    except OSError as e:
        raise RuntimeError(_("error_file_write", file=str(cfg_path), error=str(e))) from e


def read_config(cfg_path: Path) -> Dict[str, Any]:
    """读取配置文件，如果不存在则创建默认配置"""
    if not cfg_path.exists():
        # 配置文件不存在，创建默认配置文件
        create_default_config(cfg_path)
        if not cfg_path.exists():
            raise FileNotFoundError(f"配置文件创建失败：{cfg_path}")
    
    try:
        data = load_toml_bytes(cfg_path.read_bytes())
        if not isinstance(data, dict):
            raise ValueError("配置文件解析结果不是字典")
        return data
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(_("config_parse_error", file=str(cfg_path), error=str(e))) from e
    except Exception as e:
        raise RuntimeError(_("error_file_read", file=str(cfg_path), error=str(e))) from e


def validate_config(config: Dict[str, Any]) -> None:
    """验证配置文件的基本结构"""
    # 验证端口
    port = config.get("port", 2121)
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError(_("error_port_invalid", port=port))
    
    # 验证监听地址
    listen = config.get("listen", "0.0.0.0")
    if not isinstance(listen, str) or not listen.strip():
        raise ValueError(_("error_listen_invalid", listen=listen))
    
    # 验证连接限制
    max_cons = config.get("max_cons", 256)
    if not isinstance(max_cons, int) or max_cons <= 0:
        raise ValueError(_("error_max_cons_invalid", max_cons=max_cons))
    
    max_cons_per_ip = config.get("max_cons_per_ip", 10)
    if not isinstance(max_cons_per_ip, int) or max_cons_per_ip <= 0:
        raise ValueError(_("error_max_cons_per_ip_invalid", max_cons_per_ip=max_cons_per_ip))
    
    # 验证被动端口范围
    passive_ports = config.get("passive_ports")
    if passive_ports is not None:
        if not isinstance(passive_ports, (list, tuple)) or len(passive_ports) != 2:
            raise ValueError(f"被动端口范围配置无效：{passive_ports}，必须是包含两个元素的数组")
        try:
            start, end = int(passive_ports[0]), int(passive_ports[1])
            if not (1024 <= start <= 65535 and 1024 <= end <= 65535 and start <= end):
                raise ValueError(_("error_passive_ports_range_invalid", start=start, end=end))
        except (ValueError, TypeError) as e:
            raise ValueError(_("error_passive_ports_format_invalid", passive_ports=passive_ports)) from e
    
    # 验证用户配置存在
    users = config.get("users")
    if not users:
        raise ValueError(_("user_config_must_have_at_least_one"))