# -*- coding: utf-8 -*-

import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

from .config import read_config, validate_config, DEFAULT_SHARED_DIR
from .user_manager import build_authorizer, ensure_dir
from .server import apply_handler_options
from .logger import get_i18n_logger
from .i18n import _


class FTPServerManager:
    """FTP 服务器管理器"""
    
    def __init__(self, config_path: Path, shared_dir: Optional[Path] = None, port: Optional[int] = None, language: str = None):
        """
        初始化 FTP 服务器管理器
        
        Args:
            config_path: 配置文件路径
            shared_dir: 共享目录路径
            port: 监听端口（覆盖配置文件中的端口）
            language: 语言代码（zh_CN 或 en_US）
        """
        self.language = language or 'zh_CN'
        # 确保国际化实例使用正确的语言
        from .i18n import get_i18n
        get_i18n(self.language)
        
        self.logger = get_i18n_logger(__name__)
        self.config_path = config_path
        self.shared_dir = shared_dir
        self.port_override = port
        self.server: Optional[FTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        
    def _setup_shared_directory(self) -> Path:
        """设置共享目录"""
        if self.shared_dir:
            shared_dir = self.shared_dir.expanduser().resolve()
        else:
            shared_dir = (Path.cwd() / DEFAULT_SHARED_DIR).resolve()
        
        ensure_dir(shared_dir)
        return shared_dir
    
    def _load_and_validate_config(self) -> Dict[str, Any]:
        """加载并验证配置"""
        try:
            self.logger.info('config_loading')
            config = read_config(self.config_path)
            validate_config(config)
            self.logger.info('config_loaded')
            return config
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            self.logger.error('config_error', error=str(e))
            raise
    
    def _create_server(self, config: Dict[str, Any], shared_dir: Path) -> FTPServer:
        """创建 FTP 服务器实例"""
        # 端口：命令行 > 配置文件 > 默认 2121
        port = self.port_override or int(config.get("port", 2121))
        
        # 认证与用户
        try:
            authorizer = build_authorizer(config, shared_dir)
        except ValueError as e:
            self.logger.error('server_startup_failed', error=str(e))
            raise
        
        # Handler & Server
        handler = FTPHandler
        handler.authorizer = authorizer
        apply_handler_options(handler, config)
        
        address = config.get("listen", "0.0.0.0")
        server = FTPServer((address, port), handler)
        
        # 并发/性能参数
        max_cons = int(config.get("max_cons", 256))
        max_cons_per_ip = int(config.get("max_cons_per_ip", 10))
        server.max_cons = max_cons
        server.max_cons_per_ip = max_cons_per_ip
        
        return server
    
    def _log_startup_info(self, config: Dict[str, Any], shared_dir: Path) -> None:
        """输出启动信息"""
        port = self.port_override or int(config.get("port", 2121))
        address = config.get("listen", "0.0.0.0")
        
        self.logger.info('ui_separator')
        self.logger.info('server_started')
        self.logger.info('network_listening_on', host=address, port=port)
        self.logger.info('network_shared_directory', shared_dir=str(self.shared_dir))
        self.logger.info('network_config_file', config_file=str(self.config_path))
        
        users = config.get("users", [])
        self.logger.info('network_account_list')
        for u in users:
            uname = u.get("username", "")
            pwd = u.get("password", "")
            home = u.get("home", None) or str(shared_dir)
            self.logger.info(f"  - {uname} / {pwd}  -> {home}")
        
        self.logger.info('ui_separator')
        self.logger.info('tip_lan_access')
        self.logger.info(f"  ftp://<{_('network_server_ip')}>:{port}")
        self.logger.info('ui_separator')
    
    def start(self) -> None:
        """启动 FTP 服务器"""
        # 设置共享目录
        shared_dir = self._setup_shared_directory()
        
        # 加载配置
        config = self._load_and_validate_config()
        
        # 创建服务器
        self.server = self._create_server(config, shared_dir)
        
        # 输出启动信息
        self._log_startup_info(config, shared_dir)
        
        # 使用线程运行服务器，以便能够响应键盘中断
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, 
            daemon=True,
            name="FTPServerThread"
        )
        
        try:
            self.logger.info('server_running')
            self.server_thread.start()
            
            while self.server_thread.is_alive():
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info('tip_keyboard_interrupt')
        except Exception as e:
            self.logger.error('tip_runtime_error', error=str(e))
            raise
        finally:
            self.stop()
    
    def stop(self) -> None:
        """停止 FTP 服务器"""
        if self.server:
            try:
                self.server.close_all()
            except Exception as e:
                self.logger.warning('error_network', error=str(e))
        
        self.logger.info('server_stopped')
    
    def is_running(self) -> bool:
        """检查服务器是否正在运行"""
        return (
            self.server_thread is not None and 
            self.server_thread.is_alive() and 
            self.server is not None
        )