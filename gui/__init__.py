#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP2Python GUI Package

图形用户界面包，提供基于Tkinter的FTP服务器管理界面。
"""

from .main import FTPServerGUI

__all__ = ['FTPServerGUI']

def main():
    """
    GUI包的主入口函数
    """
    try:
        FTPServerGUI().run()
    except ImportError:
        return False
    except Exception:
        return False
    return True

if __name__ == '__main__':
    main()