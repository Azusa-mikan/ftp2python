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
    from .core.logger import setup_logging, get_i18n_logger
    from .core.server_manager import FTPServerManager
    from .core.i18n import get_i18n
except ImportError:
    # 回退到绝对导入（当直接运行时）
    from core.config import DEFAULT_CONFIG_NAME
    from core.logger import setup_logging, get_i18n_logger
    from core.server_manager import FTPServerManager
    from core.i18n import get_i18n


def main() -> None:
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="简单易用的 FTP 服务器 (默认启动GUI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
                "  python __init__.py                    # 启动图形用户界面 (默认)\n"
        "  python __init__.py --cli              # 启动命令行模式\n"
        "  python __init__.py --cli -c my_config.toml  # 命令行模式指定配置文件\n"
        "  python __init__.py --cli -s /path/to/share  # 命令行模式指定共享目录\n"
        "  python __init__.py --cli -p 2122            # 命令行模式指定端口\n"
        "  python __init__.py --cli -l en_US           # 命令行模式使用英文界面"
    )
    
    parser.add_argument(
        "--cli",
        action="store_true",
        help="启动命令行模式 (默认启动GUI)"
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
    
    # 在CLI模式下，如果用户没有明确指定语言参数，则不传递语言参数
    # 这样FTPServerManager会使用配置文件中的语言设置
    language_specified = any(arg in sys.argv for arg in ['-l', '--language'])
    
    # 配置日志和国际化
    setup_logging(language=args.language)
    get_i18n(args.language)
    
    # 创建logger实例
    logger = get_i18n_logger(__name__)
    
    # 如果没有指定CLI参数，默认启动GUI
    if not args.cli:
        try:
            from gui import FTPServerGUI
            app = FTPServerGUI(config_file=args.config)
            app.run()
        except ImportError:
            logger.error("gui.import_error")
            logger.error("gui.dependency_error")
            logger.info("gui.switching_to_cli")
            # 如果GUI启动失败，自动切换到CLI模式
        except Exception as e:
            logger.error("gui.startup_failed", error=str(e))
            logger.info("gui.switching_to_cli")
            # 如果GUI启动失败，自动切换到CLI模式
        else:
            return
    
    # 处理路径参数
    config_path = Path(args.config).expanduser().resolve()
    shared_dir = Path(args.shared_dir).expanduser().resolve() if args.shared_dir else None
    
    # 创建并启动服务器管理器
    try:
        # 如果用户没有明确指定语言参数，则不传递language参数
        # 这样FTPServerManager会使用配置文件中的语言设置
        if language_specified:
            server_manager = FTPServerManager(
                config_path=config_path,
                shared_dir=shared_dir,
                port=args.port,
                language=args.language
            )
        else:
            server_manager = FTPServerManager(
                config_path=config_path,
                shared_dir=shared_dir,
                port=args.port
            )
        server_manager.start()
    except Exception as e:
        import logging
        logging.error(f"服务器启动失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()