#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
轻量 FTP 服务器：
- 支持 TOML 配置（默认读取当前目录下 ftp_config.toml，可用 --config 指定）
- 支持多用户（配置文件 users 列表）
- 支持 --dir 指定共享目录；未提供则在运行目录下创建 ./shared 作为共享目录
- 如用户条目未指定 home，则使用共享目录
- 依赖：pyftpdlib；需要 Python 3.11+ 原生 tomllib
- 必须有配置文件，不存在时自动创建默认配置
"""

import argparse
import logging
import sys
import threading
import time
from pathlib import Path

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

try:
    import tomllib
except Exception:
    raise RuntimeError("此程序需要 Python 3.11 或更高版本才能运行")

def load_toml_bytes(b: bytes) -> dict:
    """加载 TOML 字节数据"""
    return tomllib.loads(b.decode("utf-8"))


DEFAULT_CONFIG_NAME = "config.toml"
DEFAULT_SHARED_DIR = "shared"


def ensure_dir(p: Path) -> Path:
    """确保目录存在，如果不存在则创建"""
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_default_config(cfg_path: Path) -> None:
    """创建默认配置文件"""
    default_config = '''# FTP 服务器配置文件

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
    
    try:
        cfg_path.write_text(default_config, encoding='utf-8')
        logging.info(f"已创建默认配置文件：{cfg_path}")
    except OSError as e:
        raise RuntimeError(f"无法创建配置文件 {cfg_path}：{e}") from e


def read_config(cfg_path: Path) -> dict:
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
    except Exception as e:
        raise RuntimeError(f"读取配置文件失败 {cfg_path}：{e}")


def build_authorizer(config: dict, shared_dir: Path) -> DummyAuthorizer:
    """
    users 配置格式示例：
    [[users]]
    username = "alice"
    password = "alicepwd"
    perm     = "elradfmw"  # 可省略，默认 elradfmw
    home     = "./data/alice"  # 可省略，省略则使用 shared_dir

    [[users]]
    username = "bob"
    password = "bobpwd"
    # 未指定 home -> 使用 shared_dir
    """
    authorizer = DummyAuthorizer()

    users = config.get("users") or []
    if not isinstance(users, list):
        raise ValueError("配置项 users 必须为数组（[[users]]）")

    # 配置文件必须包含用户配置
    if len(users) == 0:
        raise ValueError("配置文件中必须至少配置一个用户（[[users]]）")

    for u in users:
        username = str(u.get("username", "")).strip()
        password = str(u.get("password", "")).strip()
        if not username or not password:
            raise ValueError("users 中每个用户必须提供 username 与 password")

        perm = str(u.get("perm", "elradfmw"))
        home = u.get("home", None)

        if home:
            home_path = Path(home).expanduser().resolve()
            # 相对路径以配置文件/运行目录为基准都不直观，这里以当前工作目录为基准
            if not home_path.is_absolute():
                home_path = (Path.cwd() / home).resolve()
            ensure_dir(home_path)
        else:
            home_path = shared_dir

        authorizer.add_user(username, password, str(home_path), perm=perm)

    return authorizer


def apply_handler_options(handler: type[FTPHandler], config: dict) -> None:
    """应用 FTP 处理器选项配置"""
    # 可选的被动端口范围，例如：passive_ports = [50000, 50100]
    passive = config.get("passive_ports")
    if isinstance(passive, (list, tuple)) and len(passive) == 2:
        start, end = int(passive[0]), int(passive[1])
        if start <= end:
            handler.passive_ports = range(start, end + 1)

    # 欢迎语
    banner = config.get("banner")
    if isinstance(banner, str) and banner.strip():
        handler.banner = banner.strip()


def main() -> None:
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.getLogger('pyftpdlib').setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(
        description="简易多用户 FTP 服务器（TOML 可配，支持 --dir 指定共享目录）"
    )
    parser.add_argument(
        "--dir",
        dest="shared_dir",
        help=f"共享目录，未提供时在运行目录创建 ./{DEFAULT_SHARED_DIR}",
        default=None,
    )
    parser.add_argument(
        "--config",
        dest="config",
        help=f"配置文件路径（默认：{DEFAULT_CONFIG_NAME}）",
        default=DEFAULT_CONFIG_NAME,
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=int,
        help="监听端口（优先级高于配置文件 port）",
        default=None,
    )
    args = parser.parse_args()

    # 共享目录逻辑
    if args.shared_dir:
        shared_dir = Path(args.shared_dir).expanduser().resolve()
    else:
        shared_dir = (Path.cwd() / DEFAULT_SHARED_DIR).resolve()
    ensure_dir(shared_dir)

    # 读取配置
    cfg_path = Path(args.config).expanduser().resolve()
    try:
        config = read_config(cfg_path)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        logging.error(f"读取配置失败：{e}")
        sys.exit(1)

    # 端口：命令行 > 配置文件 > 默认 2121
    port = args.port or int(config.get("port", 2121))

    # 认证与用户
    try:
        authorizer = build_authorizer(config, shared_dir)
    except ValueError as e:
        logging.error(f"用户配置错误：{e}")
        sys.exit(1)

    # Handler & Server
    handler = FTPHandler
    handler.authorizer = authorizer
    apply_handler_options(handler, config)

    address = config.get("listen", "0.0.0.0")
    server = FTPServer((address, port), handler)

    # 并发/性能参数（可选）
    max_cons = int(config.get("max_cons", 256))
    max_cons_per_ip = int(config.get("max_cons_per_ip", 10))
    server.max_cons = max_cons
    server.max_cons_per_ip = max_cons_per_ip

    # 输出启动信息
    logging.info("========================================")
    logging.info("FTP 服务器启动成功")
    logging.info(f"监听地址  : {address}:{port}")
    logging.info(f"共享目录  : {shared_dir}")
    logging.info(f"配置文件  : {cfg_path}")

    users = config.get("users", [])
    logging.info("账户列表  :")
    for u in users:
        uname = u.get("username", "")
        pwd = u.get("password", "")
        home = u.get("home", None) or str(shared_dir)
        logging.info(f"  - {uname} / {pwd}  -> {home}")
    logging.info("========================================")
    logging.info("提示：同一局域网内可用 ftp 客户端连接，例如：")
    logging.info(f"  ftp://<服务器IP>:{port}")
    logging.info("========================================")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    
    try:
        logging.info("FTP 服务器正在运行，按 Ctrl+C 停止...")
        server_thread.start()
        while server_thread.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("正在退出...")
    except Exception as e:
        logging.error(f"服务器运行时发生错误：{e}")
        sys.exit(1)
    finally:
        try:
            server.close_all()
        except:
            pass
        logging.info("FTP 服务器已停止")


if __name__ == "__main__":
    main()
