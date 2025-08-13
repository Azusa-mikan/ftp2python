#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FTP2Python GUI - 图形用户界面

提供友好的图形界面来配置和管理FTP服务器
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
from pathlib import Path
from typing import Optional
import logging
import sys
import os
import queue
import datetime
import socket
import subprocess

from core.config import DEFAULT_CONFIG_NAME, read_config, validate_config, create_default_config, save_config_to_file
from core.server_manager import FTPServerManager
from core.i18n import get_i18n, _
from core.logger import setup_logging


class GUILogHandler(logging.Handler):
    """自定义日志处理器，将日志消息发送到GUI"""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


class FTPServerGUI:
    """FTP服务器图形用户界面"""
    
    def __init__(self, config_file=None, language=None):
        self.root = tk.Tk()
        
        # 服务器管理器
        self.server_manager: Optional[FTPServerManager] = None
        self.server_running = False
        
        # 配置相关
        self.config_path = Path(config_file) if config_file else Path(DEFAULT_CONFIG_NAME)
        self.config_data = {}
        
        # 日志队列和处理器
        self.log_queue = queue.Queue()
        self.gui_log_handler = None
        
        # 读取配置文件以获取语言设置
        config = read_config(self.config_path)
        
        # 确定最终使用的语言：参数 > 配置文件 > 默认值
        if language:
            self.current_language = language
        elif config and 'language' in config:
            self.current_language = config['language']
        else:
            self.current_language = 'zh_CN'
        
        # 设置国际化
        setup_logging()
        from core.i18n import init_i18n_from_config
        if not language:  # 如果没有指定语言参数，使用配置文件初始化
            init_i18n_from_config(config)
        else:  # 否则使用指定的语言
            get_i18n(language)
        self.i18n = get_i18n()
        
        # 确保全局_函数使用正确的语言
        global _
        _ = self.i18n.get
        
        # 设置窗口属性
        self.root.title(_("gui.window_title"))
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 创建界面
        self._create_widgets()
        self._load_config()
        
        # 绑定配置变量的变化事件，实现自动保存
        self._bind_config_events()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 启动日志处理
        self._start_log_processing()
    
    def _bind_config_events(self):
        """绑定配置变量的变化事件"""
        # 为所有配置相关的变量添加变化监听
        self.listen_var.trace_add('write', lambda *args: self._update_and_save_config())
        self.port_var.trace_add('write', lambda *args: self._update_and_save_config())
        self.max_cons_var.trace_add('write', lambda *args: self._update_and_save_config())
        self.max_cons_per_ip_var.trace_add('write', lambda *args: self._update_and_save_config())
        self.banner_var.trace_add('write', lambda *args: self._update_and_save_config())
        self.use_passive_var.trace_add('write', lambda *args: self._update_and_save_config())
        self.passive_start_var.trace_add('write', lambda *args: self._update_and_save_config())
        self.passive_end_var.trace_add('write', lambda *args: self._update_and_save_config())
    
    def _create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 创建语言选择框架
        self._create_language_selector(main_frame)
        
        # 创建选项卡
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(1, weight=1)
        
        # 服务器控制选项卡
        self._create_server_tab()
        
        # 配置选项卡
        self._create_config_tab()
        
        # 用户管理选项卡
        self._create_users_tab()
        
        # 日志选项卡
        self._create_log_tab()
        
        # 底部控制按钮
        self._create_control_buttons(main_frame)
    
    def _create_language_selector(self, parent):
        """创建语言选择器"""
        lang_frame = ttk.Frame(parent)
        lang_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(lang_frame, text="Language / 语言:").grid(row=0, column=0, sticky=tk.W)
        
        self.language_var = tk.StringVar(value=self.current_language)
        language_combo = ttk.Combobox(lang_frame, textvariable=self.language_var, 
                                     values=['zh_CN', 'en_US'], state='readonly', width=10)
        language_combo.grid(row=0, column=1, padx=(10, 0), sticky=tk.W)
        language_combo.bind('<<ComboboxSelected>>', self._on_language_changed)
        
        # 添加语言标签
        lang_labels = {'zh_CN': '简体中文', 'en_US': 'English'}
        current_label = lang_labels.get(self.current_language, '简体中文')
        self.lang_label = ttk.Label(lang_frame, text=f"({current_label})")
        self.lang_label.grid(row=0, column=2, padx=(5, 0), sticky=tk.W)
    
    def _on_language_changed(self, event=None):
        """语言改变事件处理"""
        new_language = self.language_var.get()
        if new_language != self.current_language:
            self.current_language = new_language
            self.i18n.set_language(new_language)
            
            # 更新全局_函数
            global _
            _ = self.i18n.get
            
            # 保存语言设置到配置文件
            self._update_and_save_config()
            
            self._refresh_ui_text()
    
    def _refresh_ui_text(self):
        """刷新界面文本"""
        # 更新窗口标题
        self.root.title(_("gui.window_title"))
        
        # 更新语言标签
        lang_labels = {'zh_CN': '简体中文', 'en_US': 'English'}
        current_label = lang_labels.get(self.current_language, '简体中文')
        self.lang_label.config(text=f"({current_label})")
        
        # 更新选项卡标题
        self.notebook.tab(0, text=_("gui.tab_server_control"))
        self.notebook.tab(1, text=_("gui.tab_server_config"))
        self.notebook.tab(2, text=_("gui.tab_user_management"))
        self.notebook.tab(3, text=_("gui.tab_log"))
        
        # 更新底部控制按钮文本
        self.start_button.config(text=_("gui.start_server"))
        self.stop_button.config(text=_("gui.stop_server"))
        
        # 更新状态文本
        if self.server_running:
            self.status_label.config(text=_("gui.server_running"))
        else:
            self.status_label.config(text=_("gui.server_not_running"))
        
        # 更新用户列表列标题
        if hasattr(self, 'users_tree'):
            self.users_tree.heading('username', text=_("gui.username"))
            self.users_tree.heading('password', text=_("gui.password"))
            self.users_tree.heading('permissions', text=_("gui.permissions"))
            self.users_tree.heading('home', text=_("gui.home_directory"))
        
        # 更新所有LabelFrame和Label的文本
        self._update_all_widget_texts()
        
        # 只有在服务器运行时才更新连接信息显示
        if self.server_running:
            self._show_connection_info()
    
    def _update_all_widget_texts(self):
        """更新所有界面控件的文本"""
        # 更新服务器控制标签页的控件
        if hasattr(self, 'server_status_frame'):
            self.server_status_frame.config(text=_("gui.server_status"))
        if hasattr(self, 'server_info_frame'):
            self.server_info_frame.config(text=_("gui.server_info"))
        if hasattr(self, 'connection_info_frame'):
            self.connection_info_frame.config(text=_("gui.connection_info"))
        if hasattr(self, 'listen_label'):
            self.listen_label.config(text=_("gui.listen_address"))
        if hasattr(self, 'port_label'):
            self.port_label.config(text=_("gui.port"))
        if hasattr(self, 'shared_dir_label'):
            self.shared_dir_label.config(text=_("gui.shared_directory"))
        if hasattr(self, 'browse_button'):
            self.browse_button.config(text=_("gui.browse"))
        
        # 更新配置标签页的控件
        if hasattr(self, 'config_file_frame'):
            self.config_file_frame.config(text=_("gui.config_file"))
        if hasattr(self, 'config_file_path_label'):
            self.config_file_path_label.config(text=_("gui.config_file_path"))
        if hasattr(self, 'config_browse_button'):
            self.config_browse_button.config(text=_("gui.browse"))
        if hasattr(self, 'config_reload_button'):
            self.config_reload_button.config(text=_("gui.reload"))
        if hasattr(self, 'basic_settings_frame'):
            self.basic_settings_frame.config(text=_("gui.basic_settings"))
        if hasattr(self, 'max_connections_label'):
            self.max_connections_label.config(text=_("gui.max_connections"))
        if hasattr(self, 'max_connections_per_ip_label'):
            self.max_connections_per_ip_label.config(text=_("gui.max_connections_per_ip"))
        if hasattr(self, 'welcome_message_label'):
            self.welcome_message_label.config(text=_("gui.welcome_message"))
        if hasattr(self, 'passive_port_frame'):
            self.passive_port_frame.config(text=_("gui.passive_port_settings"))
        if hasattr(self, 'enable_passive_checkbox'):
            self.enable_passive_checkbox.config(text=_("gui.enable_passive_ports"))
        if hasattr(self, 'start_port_label'):
            self.start_port_label.config(text=_("gui.start_port"))
        if hasattr(self, 'end_port_label'):
            self.end_port_label.config(text=_("gui.end_port"))
        
        # 更新用户管理标签页的控件
        if hasattr(self, 'user_list_frame'):
            self.user_list_frame.config(text=_("gui.user_list"))
        if hasattr(self, 'add_user_button'):
            self.add_user_button.config(text=_("gui.add_user"))
        if hasattr(self, 'edit_user_button'):
            self.edit_user_button.config(text=_("gui.edit_user"))
        if hasattr(self, 'delete_user_button'):
            self.delete_user_button.config(text=_("gui.delete_user"))
        
        # 更新日志标签页的控件
        if hasattr(self, 'clear_logs_button'):
            self.clear_logs_button.config(text=_("gui.clear_logs"))
        if hasattr(self, 'save_logs_button'):
            self.save_logs_button.config(text=_("gui.save_logs"))
        
        # 更新退出按钮
        if hasattr(self, 'exit_button'):
            self.exit_button.config(text=_("gui.exit"))
    
    def _create_server_tab(self):
        """创建服务器控制选项卡"""
        server_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(server_frame, text=_("gui.tab_server_control"))
        
        # 服务器状态
        self.server_status_frame = ttk.LabelFrame(server_frame, text=_("gui.server_status"), padding="10")
        self.server_status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(self.server_status_frame, text=_("gui.server_not_running"), font=('Arial', 12, 'bold'))
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.status_indicator = tk.Canvas(self.server_status_frame, width=20, height=20)
        self.status_indicator.grid(row=0, column=1, padx=(10, 0))
        self._update_status_indicator(False)
        
        # 服务器信息
        self.server_info_frame = ttk.LabelFrame(server_frame, text=_("gui.server_info"), padding="10")
        self.server_info_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 监听地址和端口
        self.listen_label = ttk.Label(self.server_info_frame, text=_("gui.listen_address"))
        self.listen_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.listen_var = tk.StringVar(value="0.0.0.0")
        self.listen_entry = ttk.Entry(self.server_info_frame, textvariable=self.listen_var, width=20)
        self.listen_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        self.port_label = ttk.Label(self.server_info_frame, text=_("gui.port"))
        self.port_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.port_var = tk.StringVar(value="2121")
        self.port_entry = ttk.Entry(self.server_info_frame, textvariable=self.port_var, width=10)
        self.port_entry.grid(row=0, column=3, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 共享目录
        self.shared_dir_label = ttk.Label(self.server_info_frame, text=_("gui.shared_directory"))
        self.shared_dir_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.shared_dir_var = tk.StringVar(value="./shared")
        self.shared_dir_entry = ttk.Entry(self.server_info_frame, textvariable=self.shared_dir_var, width=40)
        self.shared_dir_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        self.browse_button = ttk.Button(self.server_info_frame, text=_("gui.browse"), command=self._browse_shared_dir)
        self.browse_button.grid(row=1, column=3, padx=(10, 0), pady=2)
        
        self.server_info_frame.columnconfigure(1, weight=1)
        
        # 连接信息显示
        self.connection_info_frame = ttk.LabelFrame(server_frame, text=_("gui.connection_info"), padding="10")
        self.connection_info_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        server_frame.rowconfigure(2, weight=1)
        
        self.connection_text = scrolledtext.ScrolledText(self.connection_info_frame, height=10, state=tk.DISABLED)
        self.connection_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.connection_info_frame.columnconfigure(0, weight=1)
        self.connection_info_frame.rowconfigure(0, weight=1)
    
    def _create_config_tab(self):
        """创建配置选项卡"""
        config_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(config_frame, text=_("gui.tab_server_config"))
        
        # 配置文件选择
        self.config_file_frame = ttk.LabelFrame(config_frame, text=_("gui.config_file"), padding="10")
        self.config_file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.config_file_path_label = ttk.Label(self.config_file_frame, text=_("gui.config_file_path"))
        self.config_file_path_label.grid(row=0, column=0, sticky=tk.W)
        self.config_path_var = tk.StringVar(value=str(self.config_path))
        self.config_path_entry = ttk.Entry(self.config_file_frame, textvariable=self.config_path_var, width=50)
        self.config_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        self.config_browse_button = ttk.Button(self.config_file_frame, text=_("gui.browse"), command=self._browse_config_file)
        self.config_browse_button.grid(row=0, column=2, padx=(10, 0))
        self.config_reload_button = ttk.Button(self.config_file_frame, text=_("gui.reload"), command=self._load_config)
        self.config_reload_button.grid(row=0, column=3, padx=(10, 0))
        
        self.config_file_frame.columnconfigure(1, weight=1)
        
        # 基本设置
        self.basic_settings_frame = ttk.LabelFrame(config_frame, text=_("gui.basic_settings"), padding="10")
        self.basic_settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 最大连接数
        self.max_connections_label = ttk.Label(self.basic_settings_frame, text=_("gui.max_connections"))
        self.max_connections_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.max_cons_var = tk.StringVar(value="256")
        ttk.Entry(self.basic_settings_frame, textvariable=self.max_cons_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 每IP最大连接数
        self.max_connections_per_ip_label = ttk.Label(self.basic_settings_frame, text=_("gui.max_connections_per_ip"))
        self.max_connections_per_ip_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.max_cons_per_ip_var = tk.StringVar(value="10")
        ttk.Entry(self.basic_settings_frame, textvariable=self.max_cons_per_ip_var, width=10).grid(row=0, column=3, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 欢迎消息
        self.welcome_message_label = ttk.Label(self.basic_settings_frame, text=_("gui.welcome_message"))
        self.welcome_message_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.banner_var = tk.StringVar(value="欢迎使用 FTP 服务器")
        ttk.Entry(self.basic_settings_frame, textvariable=self.banner_var, width=50).grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        self.basic_settings_frame.columnconfigure(1, weight=1)
        
        # 被动端口设置
        self.passive_port_frame = ttk.LabelFrame(config_frame, text=_("gui.passive_port_settings"), padding="10")
        self.passive_port_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.use_passive_var = tk.BooleanVar()
        self.enable_passive_checkbox = ttk.Checkbutton(self.passive_port_frame, text=_("gui.enable_passive_ports"), variable=self.use_passive_var, 
                       command=self._toggle_passive_ports)
        self.enable_passive_checkbox.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.start_port_label = ttk.Label(self.passive_port_frame, text=_("gui.start_port"))
        self.start_port_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.passive_start_var = tk.StringVar(value="50000")
        self.passive_start_entry = ttk.Entry(self.passive_port_frame, textvariable=self.passive_start_var, width=10, state=tk.DISABLED)
        self.passive_start_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        self.end_port_label = ttk.Label(self.passive_port_frame, text=_("gui.end_port"))
        self.end_port_label.grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.passive_end_var = tk.StringVar(value="50100")
        self.passive_end_entry = ttk.Entry(self.passive_port_frame, textvariable=self.passive_end_var, width=10, state=tk.DISABLED)
        self.passive_end_entry.grid(row=1, column=3, sticky=tk.W, padx=(10, 0), pady=2)
        
        config_frame.columnconfigure(0, weight=1)
    
    def _create_users_tab(self):
        """创建用户管理选项卡"""
        users_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(users_frame, text=_("gui.tab_user_management"))
        
        # 用户列表
        self.user_list_frame = ttk.LabelFrame(users_frame, text=_("gui.user_list"), padding="10")
        self.user_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 创建Treeview
        columns = ('username', 'password', 'permissions', 'home')
        self.users_tree = ttk.Treeview(self.user_list_frame, columns=columns, show='headings', height=8)
        
        # 设置列标题
        self.users_tree.heading('username', text=_("gui.username"))
        self.users_tree.heading('password', text=_("gui.password"))
        self.users_tree.heading('permissions', text=_("gui.permissions"))
        self.users_tree.heading('home', text=_("gui.home_directory"))
        
        # 设置列宽
        self.users_tree.column('username', width=120)
        self.users_tree.column('password', width=120)
        self.users_tree.column('permissions', width=100)
        self.users_tree.column('home', width=300)
        
        self.users_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        users_scrollbar = ttk.Scrollbar(self.user_list_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        users_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.users_tree.configure(yscrollcommand=users_scrollbar.set)
        
        self.user_list_frame.columnconfigure(0, weight=1)
        self.user_list_frame.rowconfigure(0, weight=1)
        
        # 用户操作按钮
        buttons_frame = ttk.Frame(users_frame)
        buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.add_user_button = ttk.Button(buttons_frame, text=_("gui.add_user"), command=self._add_user)
        self.add_user_button.grid(row=0, column=0, padx=(0, 10))
        self.edit_user_button = ttk.Button(buttons_frame, text=_("gui.edit_user"), command=self._edit_user)
        self.edit_user_button.grid(row=0, column=1, padx=(0, 10))
        self.delete_user_button = ttk.Button(buttons_frame, text=_("gui.delete_user"), command=self._delete_user)
        self.delete_user_button.grid(row=0, column=2, padx=(0, 10))
        
        users_frame.columnconfigure(0, weight=1)
        users_frame.rowconfigure(0, weight=1)
    
    def _create_log_tab(self):
        """创建日志选项卡"""
        log_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(log_frame, text=_("gui.tab_log"))
        
        # 日志显示
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 日志控制按钮
        log_buttons_frame = ttk.Frame(log_frame)
        log_buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.clear_logs_button = ttk.Button(log_buttons_frame, text=_("gui.clear_logs"), command=self._clear_log)
        self.clear_logs_button.grid(row=0, column=0, padx=(0, 10))
        self.save_logs_button = ttk.Button(log_buttons_frame, text=_("gui.save_logs"), command=self._save_log)
        self.save_logs_button.grid(row=0, column=1)
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def _create_control_buttons(self, parent):
        """创建底部控制按钮"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 配置控制框架，使按钮左对齐
        control_frame.columnconfigure(3, weight=1)  # 让第4列占据剩余空间
        
        self.start_button = ttk.Button(control_frame, text=_("gui.start_server"), command=self._start_server)
        self.start_button.grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.stop_button = ttk.Button(control_frame, text=_("gui.stop_server"), command=self._stop_server, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 10), sticky=tk.W)
        
        self.exit_button = ttk.Button(control_frame, text=_("gui.exit"), command=self._on_closing)
        self.exit_button.grid(row=0, column=2, sticky=tk.W)
    
    def _update_status_indicator(self, running: bool):
        """更新状态指示器"""
        self.status_indicator.delete("all")
        color = "green" if running else "red"
        self.status_indicator.create_oval(2, 2, 18, 18, fill=color, outline=color)
    
    def _browse_shared_dir(self):
        """浏览共享目录"""
        directory = filedialog.askdirectory(initialdir=self.shared_dir_var.get())
        if directory:
            self.shared_dir_var.set(directory)
    
    def _browse_config_file(self):
        """浏览配置文件"""
        filename = filedialog.askopenfilename(
            initialdir=str(self.config_path.parent),
            filetypes=[("TOML files", "*.toml"), ("All files", "*.*")]
        )
        if filename:
            self.config_path_var.set(filename)
            self.config_path = Path(filename)
            self._load_config()
    
    def _toggle_passive_ports(self):
        """切换被动端口设置"""
        state = tk.NORMAL if self.use_passive_var.get() else tk.DISABLED
        self.passive_start_entry.config(state=state)
        self.passive_end_entry.config(state=state)
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_path.exists():
                self.config_data = read_config(self.config_path)
            else:
                # 创建默认配置
                create_default_config(self.config_path)
                self.config_data = read_config(self.config_path)
            
            # 更新界面
            self._update_ui_from_config()
            self._log_message(f"配置文件加载成功: {self.config_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载配置文件失败: {e}")
            self._log_message(f"配置文件加载失败: {e}")
    
    def _update_ui_from_config(self):
        """根据配置更新界面"""
        # 更新基本设置
        self.listen_var.set(self.config_data.get("listen", "0.0.0.0"))
        self.port_var.set(str(self.config_data.get("port", 2121)))
        self.max_cons_var.set(str(self.config_data.get("max_cons", 256)))
        self.max_cons_per_ip_var.set(str(self.config_data.get("max_cons_per_ip", 10)))
        self.banner_var.set(self.config_data.get("banner", "欢迎使用 FTP 服务器"))
        
        # 更新被动端口设置
        passive_ports = self.config_data.get("passive_ports")
        if passive_ports and len(passive_ports) == 2:
            self.use_passive_var.set(True)
            self.passive_start_var.set(str(passive_ports[0]))
            self.passive_end_var.set(str(passive_ports[1]))
            self._toggle_passive_ports()
        else:
            self.use_passive_var.set(False)
            self._toggle_passive_ports()
        
        # 更新用户列表
        self._update_users_tree()
    
    def _update_users_tree(self):
        """更新用户列表"""
        # 清空现有项目
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        # 添加用户
        users = self.config_data.get("users", [])
        for user in users:
            username = user.get("username", "")
            password = user.get("password", "")
            perm = user.get("perm", "elradfmw")
            home = user.get("home", "")
            
            self.users_tree.insert("", tk.END, values=(username, password, perm, home))
    
    def _save_config_to_file(self):
        """将配置保存到TOML文件"""
        save_config_to_file(self.config_data, self.config_path)
    
    def _update_and_save_config(self):
        """更新配置数据并保存到文件"""
        try:
            # 更新基本配置
            self.config_data["listen"] = self.listen_var.get()
            
            # 验证并更新端口
            try:
                port = int(self.port_var.get())
                if 1 <= port <= 65535:
                    self.config_data["port"] = port
            except ValueError:
                pass  # 忽略无效端口，保持原值
            
            # 更新其他配置
            try:
                self.config_data["max_cons"] = int(self.max_cons_var.get())
            except ValueError:
                pass
            
            try:
                self.config_data["max_cons_per_ip"] = int(self.max_cons_per_ip_var.get())
            except ValueError:
                pass
            
            self.config_data["banner"] = self.banner_var.get()
            
            # 更新语言设置
            self.config_data["language"] = self.current_language
            
            # 更新被动端口设置
            if self.use_passive_var.get():
                try:
                    start_port = int(self.passive_start_var.get())
                    end_port = int(self.passive_end_var.get())
                    if 1 <= start_port <= end_port <= 65535:
                        self.config_data["passive_ports"] = [start_port, end_port]
                except ValueError:
                    pass
            else:
                self.config_data.pop("passive_ports", None)
            
            # 保存到文件
            self._save_config_to_file()
        except Exception:
            # 静默处理保存失败，避免产生不必要的日志
            pass
    
    def _add_user(self):
        """添加用户"""
        self._show_user_dialog()
    
    def _edit_user(self):
        """编辑用户"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning(_("gui.warning"), _("gui.select_user_to_edit"))
            return
        
        item = selection[0]
        values = self.users_tree.item(item, 'values')
        user_data = {
            'username': values[0],
            'password': values[1],
            'perm': values[2],
            'home': values[3]
        }
        
        self._show_user_dialog(user_data, item)
    
    def _delete_user(self):
        """删除用户"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning(_("gui.warning"), _("gui.select_user_to_delete"))
            return
        
        if messagebox.askyesno(_("gui.confirm"), _("gui.confirm_delete_user")):
            item = selection[0]
            values = self.users_tree.item(item, 'values')
            username = values[0]
            
            # 从配置中删除用户
            users = self.config_data.get("users", [])
            self.config_data["users"] = [u for u in users if u.get("username") != username]
            
            # 更新界面
            self.users_tree.delete(item)
            self._log_message(_("gui.user_deleted", username=username))
            
            # 自动保存配置到文件
            try:
                self._save_config_to_file()
                self._log_message(_("config.saved_successfully"))
            except Exception as e:
                messagebox.showerror(_("gui.error"), _("config.save_failed", error=str(e)))
                self._log_message(_("config.save_failed", error=str(e)))
    
    def _show_user_dialog(self, user_data=None, tree_item=None):
        """显示用户编辑对话框"""
        dialog = UserDialog(self.root, user_data)
        result = dialog.result
        
        if result:
            if tree_item:
                # 编辑现有用户
                self.users_tree.item(tree_item, values=(
                    result['username'], result['password'], 
                    result['perm'], result['home']
                ))
                
                # 更新配置数据
                users = self.config_data.get("users", [])
                for user in users:
                    if user.get("username") == user_data['username']:
                        user.update(result)
                        break
            else:
                # 添加新用户
                self.users_tree.insert("", tk.END, values=(
                    result['username'], result['password'], 
                    result['perm'], result['home']
                ))
                
                # 更新配置数据
                if "users" not in self.config_data:
                    self.config_data["users"] = []
                self.config_data["users"].append(result)
            
            if tree_item:
                self._log_message(_("gui.user_updated", username=result['username']))
            else:
                self._log_message(_("gui.user_added", username=result['username']))
            
            # 自动保存配置到文件
            try:
                self._save_config_to_file()
                self._log_message(_("config.saved_successfully"))
            except Exception as e:
                messagebox.showerror(_("gui.error"), _("config.save_failed", error=str(e)))
                self._log_message(_("config.save_failed", error=str(e)))
    
    def _start_server(self):
        """启动服务器"""
        if self.server_running:
            messagebox.showwarning(_("gui.warning"), _("gui.server_already_running"))
            return
        
        try:
            # 验证端口输入
            try:
                port_value = int(self.port_var.get())
                if not (1 <= port_value <= 65535):
                    raise ValueError(_("error.port_invalid", port=port_value))
            except ValueError as e:
                if "invalid literal" in str(e):
                    messagebox.showerror(_("gui.error"), _("error.port_invalid", port=self.port_var.get()))
                else:
                    messagebox.showerror(_("gui.error"), str(e))
                return
            
            # 验证配置
            validate_config(self.config_data)
            
            # 设置日志处理器
            self._setup_server_logging()
            
            # 创建服务器管理器
            shared_dir = Path(self.shared_dir_var.get()) if self.shared_dir_var.get() else None
            port = port_value if port_value != self.config_data.get("port", 2121) else None
            
            self.server_manager = FTPServerManager(
                config_path=self.config_path,
                shared_dir=shared_dir,
                port=port,
                language=self.current_language
            )
            
            # 在新线程中启动服务器
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            # 更新界面状态
            self.server_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text=_("gui.server_running"))
            self._update_status_indicator(True)
            
            # 显示连接信息
            self._show_connection_info()
            
            self._log_message(_("server.started"))
            
        except Exception as e:
            messagebox.showerror(_("gui.error"), f"{_("gui.start_server_failed")}: {e}")
            self._log_message(f"{_("gui.start_server_failed")}: {e}")
    
    def _run_server(self):
        """在线程中运行服务器"""
        try:
            self.server_manager.start()
        except Exception as e:
            self._log_message(f"服务器运行错误: {e}")
            # 在主线程中更新界面
            self.root.after(0, self._server_stopped_callback)
    
    def _server_stopped_callback(self):
        """服务器停止回调"""
        self.server_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text=_("gui.server_not_running"))
        self._update_status_indicator(False)
        
        # 清空连接信息显示
        self.connection_text.config(state=tk.NORMAL)
        self.connection_text.delete(1.0, tk.END)
        self.connection_text.config(state=tk.DISABLED)
        
        self._log_message(_("gui.ftp_server_stopped"))
    
    def _setup_server_logging(self):
        """设置服务器日志处理器"""
        # 移除之前的处理器（如果存在）
        if self.gui_log_handler:
            logging.getLogger().removeHandler(self.gui_log_handler)
        
        # 创建新的GUI日志处理器
        self.gui_log_handler = GUILogHandler(self.log_queue)
        self.gui_log_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter('%(message)s')
        self.gui_log_handler.setFormatter(formatter)
        
        # 添加到根日志记录器
        logging.getLogger().addHandler(self.gui_log_handler)
    
    def _remove_server_logging(self):
        """移除服务器日志处理器"""
        if self.gui_log_handler:
            logging.getLogger().removeHandler(self.gui_log_handler)
            self.gui_log_handler = None
    
    def _stop_server(self):
        """停止服务器"""
        if not self.server_running:
            messagebox.showwarning(_("gui.warning"), _("gui.server_not_running"))
            return
        
        try:
            if self.server_manager:
                self.server_manager.stop()
            
            # 移除日志处理器
            self._remove_server_logging()
            
            self._server_stopped_callback()
            
        except Exception as e:
            messagebox.showerror(_("gui.error"), f"{_("gui.stop_server_failed")}: {e}")
            self._log_message(f"{_("gui.stop_server_failed")}: {e}")
    
    def _get_local_ip(self):
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
    
    def _format_connection_host(self, listen_host):
        """格式化连接主机地址"""
        if listen_host == "0.0.0.0":
            return "<本机IP>"
        elif listen_host == "127.0.0.1":
            return "仅本机连接"
        else:
            return listen_host
    
    def _get_display_host(self, listen_host):
        """获取用于显示的主机地址"""
        if listen_host == "0.0.0.0":
            return self._get_local_ip()
        else:
            return listen_host

    def _show_connection_info(self):
        """显示连接信息"""
        self.connection_text.config(state=tk.NORMAL)
        self.connection_text.delete(1.0, tk.END)
        
        listen_host = self.listen_var.get()
        port = self.port_var.get()
        shared_dir = self.shared_dir_var.get()
        
        # 获取显示用的主机地址
        display_host = self._get_display_host(listen_host)
        formatted_host = self._format_connection_host(listen_host)
        
        # 监听地址显示
        listen_display = "仅本机连接" if listen_host == "127.0.0.1" else listen_host
        
        info = f"""{_("gui.connection_info_title")}

{_("gui.listen_address")} {listen_display}
{_("gui.port")} {port}
{_("gui.shared_directory")} {shared_dir}

{_("gui.connection_methods")}
{_("gui.ftp_client_method")}
{_("gui.ftp_client_host", host=formatted_host)}
{_("gui.ftp_client_port", port=port)}
{_("gui.ftp_client_credentials")}

{_("gui.command_line_method")}
{_("gui.command_line_example", host=display_host, port=port)}

{_("gui.browser_method")}
{_("gui.browser_example", host=display_host, port=port)}
"""
        
        self.connection_text.insert(tk.END, info)
        self.connection_text.config(state=tk.DISABLED)
    
    def _start_log_processing(self):
        """启动日志处理"""
        self._process_log_queue()
    
    def _process_log_queue(self):
        """处理日志队列中的消息"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self._log_message(message)
        except queue.Empty:
            pass
        
        # 每100ms检查一次队列
        self.root.after(100, self._process_log_queue)
    
    def _log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _save_log(self):
        """保存日志"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo(_("gui.success"), _("gui.log_saved_success"))
            except Exception as e:
                messagebox.showerror(_("gui.error"), f"{_("gui.log_save_failed")}: {e}")
    
    def _on_closing(self):
        """关闭程序"""
        if self.server_running:
            if messagebox.askyesno(_("gui.confirm"), _("gui.server_is_running_exit")):
                self._stop_server()
                # 移除日志处理器
                self._remove_server_logging()
                self.root.destroy()
        else:
            # 移除日志处理器
            self._remove_server_logging()
            self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


class UserDialog:
    """用户编辑对话框"""
    
    def __init__(self, parent, user_data=None):
        self.result = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_("gui.edit_user") if user_data else _("gui.add_user"))
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # 创建界面
        self._create_widgets(user_data)
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def _create_widgets(self, user_data):
        """创建对话框组件"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 用户名
        ttk.Label(main_frame, text=_("gui.username") + ":").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar(value=user_data.get('username', '') if user_data else '')
        ttk.Entry(main_frame, textvariable=self.username_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 密码
        ttk.Label(main_frame, text=_("gui.password") + ":").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar(value=user_data.get('password', '') if user_data else '')
        ttk.Entry(main_frame, textvariable=self.password_var, width=30, show="*").grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 权限
        ttk.Label(main_frame, text=_("gui.permissions") + ":").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.perm_var = tk.StringVar(value=user_data.get('perm', 'elradfmw') if user_data else 'elradfmw')
        perm_frame = ttk.Frame(main_frame)
        perm_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(perm_frame, textvariable=self.perm_var, width=15).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(perm_frame, text=_("gui.user_permissions_hint"), 
                 font=('Arial', 8)).grid(row=1, column=0, sticky=tk.W)
        
        # 主目录
        ttk.Label(main_frame, text=_("gui.home_directory") + ":").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.home_var = tk.StringVar(value=user_data.get('home', '') if user_data else '')
        home_frame = ttk.Frame(main_frame)
        home_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(home_frame, textvariable=self.home_var, width=25).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(home_frame, text=_("gui.browse"), command=self._browse_home).grid(row=0, column=1, padx=(5, 0))
        home_frame.columnconfigure(0, weight=1)
        
        ttk.Label(main_frame, text=_("gui.home_directory_hint"), font=('Arial', 8)).grid(row=4, column=1, sticky=tk.W)
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text=_("gui.ok"), command=self._ok_clicked).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text=_("gui.cancel"), command=self._cancel_clicked).grid(row=0, column=1)
        
        main_frame.columnconfigure(1, weight=1)
    
    def _browse_home(self):
        """浏览主目录"""
        directory = filedialog.askdirectory(initialdir=self.home_var.get() or os.getcwd())
        if directory:
            self.home_var.set(directory)
    
    def _ok_clicked(self):
        """确定按钮点击"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        perm = self.perm_var.get().strip()
        home = self.home_var.get().strip()
        
        if not username:
            messagebox.showerror(_("gui.error"), _("gui.username_cannot_be_empty"))
            return
        
        if not password:
            messagebox.showerror(_("gui.error"), _("gui.password_cannot_be_empty"))
            return
        
        # 验证权限字符串
        valid_perms = set("elradfmw")
        if not all(p in valid_perms for p in perm):
            messagebox.showerror(_("gui.error"), _("gui.invalid_permission_string"))
            return
        
        self.result = {
            'username': username,
            'password': password,
            'perm': perm,
            'home': home
        }
        
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        """取消按钮点击"""
        self.dialog.destroy()


def main():
    """GUI主函数"""
    try:
        app = FTPServerGUI()
        app.run()
    except Exception as e:
        messagebox.showerror(_("gui.error"), f"{_("gui.start_gui_failed")}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()