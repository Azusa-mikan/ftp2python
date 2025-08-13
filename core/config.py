# -*- coding: utf-8 -*-
"""
配置文件管理模块

提供FTP服务器配置文件的读取、写入、验证和管理功能。
支持TOML格式的配置文件，确保CLI和GUI模式使用统一的配置格式。
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple

from .i18n import _

try:
    import tomllib
except ImportError:
    import tomli as tomllib

try:
    import tomli_w
except ImportError:
    tomli_w = None


# 常量定义
DEFAULT_CONFIG_NAME: str = "config.toml"
DEFAULT_SHARED_DIR: str = "shared"

# 端口范围常量
MIN_PORT: int = 1
MAX_PORT: int = 65535
MIN_PASSIVE_PORT: int = 1024

# 默认配置数据
DEFAULT_CONFIG_DATA: Dict[str, Any] = {
    "port": 2121,
    "listen": "0.0.0.0",
    "max_cons": 256,
    "max_cons_per_ip": 10,
    "banner": "欢迎使用 FTP 服务器",
    "language": "zh_CN",
    "users": [
        {
            "username": "user",
            "password": "123456",
            "perm": "elradfmw"
        }
    ]
}

def load_toml_bytes(data: bytes) -> Dict[str, Any]:
    """加载 TOML 字节数据
    
    Args:
        data: TOML格式的字节数据
        
    Returns:
        解析后的配置字典
        
    Raises:
        UnicodeDecodeError: 字节数据无法解码为UTF-8
        tomllib.TOMLDecodeError: TOML格式解析错误
    """
    try:
        text = data.decode("utf-8")
        return tomllib.loads(text)
    except UnicodeDecodeError as e:
        raise ValueError(_("config.encoding_error", error=str(e))) from e
    except tomllib.TOMLDecodeError as e:
        raise ValueError(_("config.parse_error", error=str(e))) from e


def create_default_config(cfg_path: Path) -> None:
    """创建默认配置文件"""
    try:
        # 使用统一的配置保存函数
        save_config_to_file(DEFAULT_CONFIG_DATA, cfg_path)
        logging.info(_("config.created", path=str(cfg_path)))
    except OSError as e:
        raise RuntimeError(_("error.file_write", file=str(cfg_path), error=str(e))) from e


def _generate_commented_toml(config_data: Dict[str, Any]) -> str:
    """生成带注释的TOML配置内容
    
    Args:
        config_data: 配置数据字典
        
    Returns:
        带注释的TOML格式字符串
    """
    lines = []
    lines.append("# FTP服务器配置文件")
    lines.append("# 此文件包含FTP服务器的所有配置选项")
    lines.append("")
    
    # 端口配置
    lines.append("# FTP服务器监听端口 (1-65535)")
    lines.append("# 默认: 2121 (避免与系统FTP端口21冲突)")
    lines.append(f"port = {config_data.get('port', 2121)}")
    lines.append("")
    
    # 监听地址配置
    lines.append("# 服务器监听地址")
    lines.append("# 0.0.0.0 = 监听所有网络接口")
    lines.append("# 127.0.0.1 = 仅本地访问")
    lines.append(f"listen = \"{config_data.get('listen', '0.0.0.0')}\"")
    lines.append("")
    
    # 连接数限制
    lines.append("# 最大同时连接数")
    lines.append("# 建议值: 256 (根据服务器性能调整)")
    lines.append(f"max_cons = {config_data.get('max_cons', 256)}")
    lines.append("")
    
    # 单IP连接数限制
    lines.append("# 每个IP地址的最大连接数")
    lines.append("# 防止单个客户端占用过多连接")
    lines.append(f"max_cons_per_ip = {config_data.get('max_cons_per_ip', 10)}")
    lines.append("")
    
    # 欢迎横幅
    lines.append("# FTP服务器欢迎消息")
    lines.append("# 客户端连接时显示的消息")
    banner = config_data.get('banner', '欢迎使用 FTP 服务器')
    lines.append(f"banner = \"{banner}\"")
    lines.append("")
    
    # 语言配置
    lines.append("# 界面语言设置")
    lines.append("# 支持的语言: zh_CN (简体中文), en_US (English)")
    lines.append("# 重启服务器后生效")
    language = config_data.get('language', 'zh_CN')
    lines.append(f"language = \"{language}\"")
    lines.append("")
    
    # 被动模式端口范围（如果存在）
    if 'passive_ports' in config_data:
        lines.append("# 被动模式端口范围")
        lines.append("# 格式: [起始端口, 结束端口]")
        lines.append("# 确保防火墙开放这些端口")
        passive_ports = config_data['passive_ports']
        lines.append(f"passive_ports = [{passive_ports[0]}, {passive_ports[1]}]")
        lines.append("")
    
    # 用户配置
    lines.append("# 用户账户配置")
    lines.append("# 每个用户包含: username(用户名), password(密码), perm(权限)")
    lines.append("# 权限说明:")
    lines.append("#   e = 更改目录 (CWD, CDUP)")
    lines.append("#   l = 列出文件 (LIST, NLST, STAT, MLSD, MLST)")
    lines.append("#   r = 从服务器检索文件 (RETR)")
    lines.append("#   a = 向服务器追加数据 (APPE)")
    lines.append("#   d = 删除文件和目录 (DELE, RMD)")
    lines.append("#   f = 重命名文件和目录 (RNFR, RNTO)")
    lines.append("#   m = 创建目录 (MKD)")
    lines.append("#   w = 向服务器存储文件 (STOR, STOU)")
    lines.append("")
    
    users = config_data.get('users', [])
    for i, user in enumerate(users):
        if i == 0:
            lines.append("[[users]]")
        else:
            lines.append("")
            lines.append("[[users]]")
        
        username = user.get('username', 'user')
        password = user.get('password', '123456')
        perm = user.get('perm', 'elradfmw')
        
        lines.append(f"username = \"{username}\"")
        lines.append(f"password = \"{password}\"")
        lines.append(f"perm = \"{perm}\"")
        
        # 添加用户特定的主目录（如果存在）
        if 'home_dir' in user:
            lines.append(f"home_dir = \"{user['home_dir']}\"")
    
    return "\n".join(lines) + "\n"


def save_config_to_file(config_data: Dict[str, Any], cfg_path: Path) -> None:
    """统一的配置文件保存函数
    
    确保CLI和GUI模式都使用相同的TOML格式保存配置文件，并添加详细注释。
    
    Args:
        config_data: 要保存的配置数据字典
        cfg_path: 配置文件路径
        
    Raises:
        ImportError: tomli_w库未安装
        RuntimeError: 文件写入失败
        ValueError: 配置数据格式无效
    """
    if not isinstance(config_data, dict):
        raise ValueError("配置数据必须是字典类型")
    
    # 创建配置数据的深拷贝，避免修改原始数据
    import copy
    config_copy = copy.deepcopy(config_data)
    
    # 确保父目录存在
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # 手动构建带注释的TOML内容
        toml_content = _generate_commented_toml(config_copy)
        
        with open(cfg_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        # 移除日志输出，避免在GUI自动保存时产生不必要的日志
    except (OSError, IOError) as e:
        raise RuntimeError(_("error.file_write", file=str(cfg_path), error=str(e))) from e
    except Exception as e:
        raise RuntimeError(f"保存配置文件时发生未知错误: {e}") from e


def read_config(cfg_path: Path) -> Dict[str, Any]:
    """读取配置文件，如果不存在则创建默认配置
    
    Args:
        cfg_path: 配置文件路径
        
    Returns:
        配置数据字典
        
    Raises:
        FileNotFoundError: 配置文件创建失败
        RuntimeError: 文件读取或解析失败
        ValueError: 配置文件格式无效
    """
    if not cfg_path.exists():
        logging.info(_("config.creating_default", path=str(cfg_path)))
        create_default_config(cfg_path)
        if not cfg_path.exists():
            raise FileNotFoundError(f"配置文件创建失败：{cfg_path}")
    
    try:
        file_data = cfg_path.read_bytes()
        data = load_toml_bytes(file_data)
        
        if not isinstance(data, dict):
            raise ValueError(_("config.invalid_format", file=str(cfg_path)))
            
        # 验证配置文件的基本结构
        validate_config(data)
        
        return data
        
    except (OSError, IOError) as e:
        raise RuntimeError(_("error.file_read", file=str(cfg_path), error=str(e))) from e
    except (ValueError, tomllib.TOMLDecodeError) as e:
        # 这些异常已经在load_toml_bytes或validate_config中处理过了
        raise
    except Exception as e:
        raise RuntimeError(f"读取配置文件时发生未知错误: {e}") from e


def _validate_port(port: Any) -> None:
    """验证端口配置
    
    Args:
        port: 端口值
        
    Raises:
        ValueError: 端口配置无效
    """
    if not isinstance(port, int) or not (MIN_PORT <= port <= MAX_PORT):
        raise ValueError(_("error.port_invalid", port=port))


def _validate_listen_address(listen: Any) -> None:
    """验证监听地址配置
    
    Args:
        listen: 监听地址
        
    Raises:
        ValueError: 监听地址配置无效
    """
    if not isinstance(listen, str) or not listen.strip():
        raise ValueError(_("error.listen_invalid", listen=listen))


def _validate_connection_limits(max_cons: Any, max_cons_per_ip: Any) -> None:
    """验证连接限制配置
    
    Args:
        max_cons: 最大连接数
        max_cons_per_ip: 每个IP最大连接数
        
    Raises:
        ValueError: 连接限制配置无效
    """
    if not isinstance(max_cons, int) or max_cons <= 0:
        raise ValueError(_("error.max_cons_invalid", max_cons=max_cons))
    
    if not isinstance(max_cons_per_ip, int) or max_cons_per_ip <= 0:
        raise ValueError(_("error.max_cons_per_ip_invalid", max_cons_per_ip=max_cons_per_ip))


def _validate_passive_ports(passive_ports: Optional[Union[List, Tuple]]) -> None:
    """验证被动端口范围配置
    
    Args:
        passive_ports: 被动端口范围
        
    Raises:
        ValueError: 被动端口范围配置无效
    """
    if passive_ports is None:
        return
        
    if not isinstance(passive_ports, (list, tuple)) or len(passive_ports) != 2:
        raise ValueError(_("passive_ports.format_invalid", passive_ports=passive_ports))
    
    try:
        start, end = int(passive_ports[0]), int(passive_ports[1])
        if not (MIN_PASSIVE_PORT <= start <= MAX_PORT and 
                MIN_PASSIVE_PORT <= end <= MAX_PORT and 
                start <= end):
            raise ValueError(_("passive_ports.range_invalid", start=start, end=end))
    except (ValueError, TypeError) as e:
        raise ValueError(_("passive_ports.format_invalid", passive_ports=passive_ports)) from e


def _validate_users(users: Any) -> None:
    """验证用户配置
    
    Args:
        users: 用户配置列表
        
    Raises:
        ValueError: 用户配置无效
    """
    if not users:
        raise ValueError(_("user.config_must_have_at_least_one"))
    
    if not isinstance(users, list):
        raise ValueError(_("user.config_must_be_list"))
    
    for i, user in enumerate(users):
        if not isinstance(user, dict):
            raise ValueError(_("user_config.must_be_dict", index=i+1))
        
        # 验证必需字段
        required_fields = ["username", "password", "perm"]
        for field in required_fields:
            if field not in user:
                raise ValueError(_("user_config.missing_field", index=i+1, field=field))
            if not isinstance(user[field], str) or not user[field].strip():
                raise ValueError(_("user_config.field_empty", index=i+1, field=field))


def validate_config(config: Dict[str, Any]) -> None:
    """验证配置文件的完整性和正确性
    
    Args:
        config: 配置数据字典
        
    Raises:
        ValueError: 配置验证失败
    """
    if not isinstance(config, dict):
        raise ValueError("配置数据必须是字典格式")
    
    # 验证各个配置项
    _validate_port(config.get("port", 2121))
    _validate_listen_address(config.get("listen", "0.0.0.0"))
    _validate_connection_limits(
        config.get("max_cons", 256),
        config.get("max_cons_per_ip", 10)
    )
    _validate_passive_ports(config.get("passive_ports"))
    _validate_users(config.get("users"))
    
    # 验证横幅消息（可选）
    banner = config.get("banner")
    if banner is not None and not isinstance(banner, str):
        raise ValueError("横幅消息必须是字符串格式")