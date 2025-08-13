# -*- coding: utf-8 -*-

import threading
import time
import socket
import subprocess
import os
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
            language: 语言代码（zh_CN 或 en_US），如果为None则从配置文件读取
        """
        self.config_path = config_path
        self.shared_dir = shared_dir
        self.port_override = port
        self.language_override = language
        
        # 先读取配置文件以获取语言设置
        config = read_config(config_path)
        
        # 确定最终使用的语言：命令行参数 > 配置文件 > 默认值
        if language:
            self.language = language
        elif config and 'language' in config:
            self.language = config['language']
        else:
            self.language = 'zh_CN'
        
        # 初始化国际化设置
        from .i18n import init_i18n_from_config, get_i18n
        if not language:  # 如果没有命令行语言参数，使用配置文件初始化
            init_i18n_from_config(config)
        else:  # 否则使用命令行参数
            get_i18n(self.language)
        
        self.logger = get_i18n_logger(__name__)
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
            self.logger.info('config.loading')
            config = read_config(self.config_path)
            validate_config(config)
            self.logger.info('config.loaded')
            return config
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            self.logger.error('config.error', error=str(e))
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
        
        self.logger.info('ui.separator')
        self.logger.info('server.started')
        self.logger.info('network.listening_on', host=address, port=port)
        self.logger.info('network.shared_directory', shared_dir=str(shared_dir))
        self.logger.info('network.config_file', config_file=str(self.config_path))
        
        users = config.get("users", [])
        self.logger.info('network.account_list')
        for u in users:
            uname = u.get("username", "")
            pwd = u.get("password", "")
            home = u.get("home", None) or str(shared_dir)
            self.logger.info('user.account_info', username=uname, password=pwd, home=home)
        
        self.logger.info('ui.separator')
        self.logger.info('tip.lan_access')
        # 获取实际的本机IP地址
        local_ip = self._get_local_ip()
        self.logger.info(f"  ftp://{local_ip}:{port}")
        self.logger.info('ui.separator')
    
    def start(self) -> None:
        """启动 FTP 服务器"""
        # 设置共享目录
        shared_dir = self._setup_shared_directory()
        
        # 先读取配置文件以获取语言设置，但不验证
        try:
            from .config import read_config
            temp_config = read_config(self.config_path)
        except Exception:
            temp_config = {}
        
        # 重新初始化国际化设置（确保使用配置文件中的语言设置）
        from .i18n import init_i18n_from_config, get_i18n
        
        if not self.language_override and temp_config and 'language' in temp_config:
            init_i18n_from_config(temp_config)
            # 重新创建logger以使用新的语言设置
            self.logger = get_i18n_logger(__name__)
        
        # 加载并验证配置
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
            self.logger.info('server.running')
            self.server_thread.start()
            
            while self.server_thread.is_alive():
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info('tip.keyboard_interrupt')
        except Exception as e:
            self.logger.error('tip.runtime_error', error=str(e))
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
        
        self.logger.info('server.stopped')
    
    def _get_local_ip(self) -> str:
        """获取本机IP地址"""
        # 方法1: 尝试通过socket.gethostbyname获取
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # 避免返回127.0.0.1
            if local_ip != "127.0.0.1":
                return local_ip
        except Exception:
            pass
        
        # 方法2: 尝试连接到外部地址（不依赖特定DNS）
        external_addresses = [
            ("8.8.8.8", 80),      # Google DNS
            ("1.1.1.1", 80),      # Cloudflare DNS
            ("114.114.114.114", 80), # 114 DNS
            ("223.5.5.5", 80),    # 阿里DNS
        ]
        
        for addr, port in external_addresses:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(1)  # 设置1秒超时
                    s.connect((addr, port))
                    return s.getsockname()[0]
            except Exception:
                continue
        
        # 方法3: 尝试使用系统命令获取IP（多平台兼容）
        try:
            if os.name == 'nt':  # Windows
                # 使用ipconfig命令
                result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'IPv4' in line and ('地址' in line or 'Address' in line):
                            ip = line.split(':')[-1].strip()
                            if ip and not ip.startswith('127.') and not ip.startswith('169.254.'):
                                return ip
            else:  # Linux/Unix/macOS
                # 尝试多种命令获取IP
                commands = [
                    ['hostname', '-I'],  # Linux
                    ['hostname', '-i'],  # 某些Linux发行版
                    ['ifconfig'],        # macOS和某些Unix系统
                    ['ip', 'route', 'get', '1.1.1.1'],  # 现代Linux系统
                ]
                
                for cmd in commands:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            if cmd[0] == 'hostname':
                                # hostname命令的输出处理
                                ips = result.stdout.strip().split()
                                for ip in ips:
                                    if ip and not ip.startswith('127.') and not ip.startswith('169.254.') and '.' in ip:
                                        return ip
                            elif cmd[0] == 'ifconfig':
                                # ifconfig命令的输出处理
                                lines = result.stdout.split('\n')
                                for line in lines:
                                    if 'inet ' in line and 'netmask' in line:
                                        parts = line.strip().split()
                                        for i, part in enumerate(parts):
                                            if part == 'inet' and i + 1 < len(parts):
                                                ip = parts[i + 1]
                                                if ip and not ip.startswith('127.') and not ip.startswith('169.254.'):
                                                    return ip
                            elif cmd[0] == 'ip' and 'route' in cmd:
                                # ip route命令的输出处理
                                lines = result.stdout.split('\n')
                                for line in lines:
                                    if 'src' in line:
                                        parts = line.split()
                                        for i, part in enumerate(parts):
                                            if part == 'src' and i + 1 < len(parts):
                                                ip = parts[i + 1]
                                                if ip and not ip.startswith('127.') and not ip.startswith('169.254.'):
                                                    return ip
                    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                        continue
        except Exception:
            pass
        
        # 方法4: 尝试获取所有网络接口
        try:
            import netifaces
            for interface in netifaces.interfaces():
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    for addr_info in addresses[netifaces.AF_INET]:
                        ip = addr_info['addr']
                        # 排除回环地址和链路本地地址
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            return ip
        except ImportError:
            # netifaces模块不可用
            pass
        except Exception:
            pass
        
        # 如果所有方法都失败，返回localhost
        return "127.0.0.1"

    def is_running(self) -> bool:
        """检查服务器是否正在运行"""
        return (
            self.server_thread is not None and 
            self.server_thread.is_alive() and 
            self.server is not None
        )