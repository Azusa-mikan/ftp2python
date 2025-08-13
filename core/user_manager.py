# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from typing import Dict, Any, List
from pyftpdlib.authorizers import DummyAuthorizer
from .i18n import _
from .logger import get_i18n_logger


def ensure_dir(p: Path) -> Path:
    """确保目录存在，如果不存在则创建"""
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_authorizer(config: Dict[str, Any], shared_dir: Path) -> DummyAuthorizer:
    """
    构建用户授权器
    
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
    # 每次调用时重新获取logger，确保使用最新的国际化设置
    logger = get_i18n_logger(__name__)

    users = config.get("users") or []
    # 使用专门的验证函数
    validate_user_config(users)

    for u in users:
        username = str(u.get("username", "")).strip()
        password = str(u.get("password", "")).strip()
        if not username or not password:
            raise ValueError(_("user.must_provide_username_password"))

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
        logger.info("user.added", username=username, home_path=str(home_path))

    return authorizer


def validate_user_config(users: List[Dict[str, Any]]) -> None:
    """
    验证用户配置的有效性
    
    Args:
        users: 用户配置列表
        
    Raises:
        ValueError: 当配置无效时
    """
    if not isinstance(users, list):
        raise ValueError(_("user.config_must_be_array"))

    if len(users) == 0:
        raise ValueError(_("user.config_must_have_at_least_one"))

    usernames = set()
    for i, user in enumerate(users):
        if not isinstance(user, dict):
            raise ValueError(_("user_config.must_be_dict", index=i+1))
            
        username = str(user.get("username", "")).strip()
        password = str(user.get("password", "")).strip()
        
        if not username:
            raise ValueError(_("user_config.missing_username", index=i+1))
        if not password:
            raise ValueError(_("user_config.missing_password", index=i+1))
            
        if username in usernames:
            raise ValueError(_("user_config.duplicate_username", username=username))
        usernames.add(username)
        
        # 验证权限字符串
        perm = str(user.get("perm", "elradfmw"))
        valid_perms = set("elradfmw")
        if not all(p in valid_perms for p in perm):
            raise ValueError(_("user_config.invalid_permission", username=username, perm=perm))