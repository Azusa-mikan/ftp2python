#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FTP2Python - 轻量 FTP 服务器包

主要功能：
- 支持 TOML 配置（默认读取当前目录下 config.toml，可用 --config 指定）
- 支持多用户（配置文件 users 列表）
- 支持 --dir 指定共享目录；未提供则在运行目录下创建 ./shared 作为共享目录
- 如用户条目未指定 home，则使用共享目录
- 依赖：pyftpdlib；需要 Python 3.11+ 原生 tomllib
- 必须有配置文件，不存在时自动创建默认配置
"""

import argparse
import sys
from pathlib import Path

try:
    # 尝试相对导入（当作为包使用时）
    from .core.config import DEFAULT_CONFIG_NAME
    from .core.logger import setup_logging
    from .core.server_manager import FTPServerManager
    from .core.i18n import get_i18n
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from core.config import DEFAULT_CONFIG_NAME
    from core.logger import setup_logging
    from core.server_manager import FTPServerManager
    from core.i18n import get_i18n


def main() -> None:
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="简单易用的 FTP 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
                "  python -m ftp2python                    # 使用默认配置\n"
                "  python -m ftp2python -c my_config.toml  # 指定配置文件\n"
                "  python -m ftp2python -s /path/to/share  # 指定共享目录\n"
                "  python -m ftp2python -p 2122            # 指定端口\n"
                "  python -m ftp2python -l en_US           # 使用英文界面"
    )
    
    parser.add_argument(
        "-c", "--config",
        default=DEFAULT_CONFIG_NAME,
        help=f"配置文件路径（默认：{DEFAULT_CONFIG_NAME}）"
    )
    parser.add_argument(
        "-s", "--shared-dir",
        help="共享目录路径（默认：当前目录下的 shared 文件夹）"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        help="FTP 服务器端口（默认：配置文件中的端口或 2121）"
    )
    parser.add_argument(
        "-l", "--language",
        default="zh_CN",
        help="界面语言（支持：zh_CN, en_US, zh, en, chinese, english 等，默认：zh_CN）"
    )
    
    args = parser.parse_args()
    
    # 配置日志和国际化
    setup_logging(language=args.language)
    get_i18n(args.language)

    # 处理路径参数
    config_path = Path(args.config).expanduser().resolve()
    shared_dir = Path(args.shared_dir).expanduser().resolve() if args.shared_dir else None
    
    # 创建并启动服务器管理器
    try:
        server_manager = FTPServerManager(
            config_path=config_path,
            shared_dir=shared_dir,
            port=args.port,
            language=args.language
        )
        server_manager.start()
    except Exception as e:
        import logging
        logging.error(f"服务器启动失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()