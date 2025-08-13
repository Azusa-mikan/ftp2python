# FTP2Python

一个简单易用的轻量级 FTP 服务器，基于 Python 开发，支持多用户、多语言界面和灵活的配置管理。

## ✨ 主要特性

- 🚀 **开箱即用**：自动创建默认配置，无需复杂设置
- 👥 **多用户支持**：支持配置多个用户账户，每个用户可设置独立的权限和主目录
- 🌍 **国际化支持**：内置中文和英文界面，支持动态语言切换
- ⚙️ **灵活配置**：基于 TOML 格式的配置文件，支持命令行参数覆盖
- 🔒 **权限控制**：细粒度的用户权限管理（读取、写入、删除、重命名等）
- 🌐 **网络优化**：支持被动模式端口范围配置、连接数限制等
- 📝 **详细日志**：完整的操作日志记录，支持多语言日志消息
- 🎯 **轻量级**：基于 pyftpdlib，性能优异，资源占用低

## 📋 系统要求

- Python 3.11+ （需要原生 tomllib 支持）
- 或 Python 3.7+ （需要安装 tomli 包）

## 🚀 快速开始

### 重要提示

⚠️ **为了正确运行 `python -m ftp2python` 命令，您必须将项目克隆到一个独立的文件夹中。** 这是因为 Python 模块导入机制需要正确的包结构。

```bash
mkdir sharefile && cd sharefile
git clone https://github.com/Thomecloud/ftp2python
cd ftp2python

# 然后安装依赖并运行
pip install -r requirements.txt
cd ..
python -m ftp2python
```

### 基本使用

```bash
# 使用默认配置启动（会自动创建 config.toml 和 shared 目录）
python -m ftp2python

# 指定配置文件
python -m ftp2python -c my_config.toml

# 指定共享目录
python -m ftp2python -s /path/to/share

# 指定端口
python -m ftp2python -p 2122

# 使用英文界面
python -m ftp2python -l en_US
```

### 命令行参数

| 参数 | 长参数 | 说明 | 默认值 |
|------|--------|------|--------|
| `-c` | `--config` | 配置文件路径 | `config.toml` |
| `-s` | `--shared-dir` | 共享目录路径 | `./shared` |
| `-p` | `--port` | FTP 服务器端口 | 配置文件中的端口或 2121 |
| `-l` | `--language` | 界面语言 | `zh_CN` |

## ⚙️ 配置文件

项目使用 TOML 格式的配置文件。首次运行时会自动创建默认配置文件 `config.toml`：

```toml
# FTP 服务器配置文件

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
perm = "elradfmw" # 权限配置
# home = "./data/user"  # 可选，不指定则使用共享目录
```

### 配置项说明

#### 服务器设置
- `port`：FTP 服务器监听端口（1-65535）
- `listen`：监听地址（默认 "0.0.0.0" 表示监听所有网络接口）

#### 连接限制
- `max_cons`：最大同时连接数
- `max_cons_per_ip`：每个 IP 地址的最大连接数

#### 网络设置
- `passive_ports`：被动模式端口范围，格式为 `[起始端口, 结束端口]`
- `banner`：FTP 服务器欢迎消息

#### 用户配置
每个用户使用 `[[users]]` 块定义：

- `username`：用户名（必需）
- `password`：密码（必需）
- `perm`：权限字符串（可选，默认 "elradfmw"）
- `home`：用户主目录（可选，不指定则使用共享目录）

#### 权限字符说明
- `e`：进入目录
- `l`：列出目录内容
- `r`：读取文件
- `a`：追加文件
- `d`：删除文件/目录
- `f`：重命名文件/目录
- `m`：创建目录
- `w`：写入文件

## 🌍 多语言支持

项目支持以下语言：
- 简体中文（zh_CN）
- 英语（en_US）

支持的语言代码格式：
- `zh_CN`, `zh`, `chinese` → 简体中文
- `en_US`, `en`, `english` → 英语

## 📁 项目结构

```
ftp2python/
├── __init__.py          # 主入口模块
├── __main__.py          # 命令行入口
├── requirements.txt     # 依赖列表
└── core/               # 核心模块
    ├── config.py       # 配置管理
    ├── i18n.py         # 国际化支持
    ├── logger.py       # 日志系统
    ├── server.py       # FTP 服务器核心
    ├── server_manager.py # 服务器管理器
    ├── user_manager.py # 用户管理
    └── locales/        # 语言文件
        ├── zh_CN.toml  # 中文翻译
        └── en_US.toml  # 英文翻译
```

## 🔧 开发说明

### 核心模块

- **config.py**：配置文件读取、验证和默认配置生成
- **server_manager.py**：FTP 服务器生命周期管理
- **user_manager.py**：用户认证和权限管理
- **i18n.py**：国际化支持，多语言消息管理
- **logger.py**：日志系统，支持国际化日志消息
- **server.py**：FTP 处理器选项配置

### 扩展语言支持

1. 在 `core/locales/` 目录下创建新的语言文件（如 `fr_FR.toml`）
2. 在 `i18n.py` 的 `_normalize_language` 方法中添加语言映射
3. 在 `_load_messages` 方法的 `supported_languages` 列表中添加新语言

## 📝 使用示例

### 基本文件服务器

```bash
# 启动默认配置的 FTP 服务器
python -m ftp2python

# 服务器将在 2121 端口启动
# 默认用户：user/123456
# 共享目录：./shared
```

### 自定义配置

创建自定义配置文件 `my_ftp.toml`：

```toml
port = 2122
listen = "192.168.1.100"
banner = "欢迎访问我的文件服务器"

[[users]]
username = "admin"
password = "admin123"
perm = "elradfmw"
home = "./admin_files"

[[users]]
username = "guest"
password = "guest123"
perm = "elr"  # 只读权限
```

启动服务器：

```bash
python -m ftp2python -c my_ftp.toml
```

### 客户端连接

使用任何 FTP 客户端连接：

```bash
# 命令行 FTP 客户端
ftp localhost 2121

# 或使用图形界面客户端（如 FileZilla）
# 主机：localhost
# 端口：2121
# 用户名：user
# 密码：123456
```

## 🛠️ 故障排除

### 常见问题

1. **端口被占用**
   ```
   错误：[Errno 10048] 通常每个套接字地址只允许使用一次
   ```
   解决：更改配置文件中的端口号或使用 `-p` 参数指定其他端口

2. **权限错误**
   ```
   错误：权限被拒绝
   ```
   解决：确保共享目录和用户主目录具有适当的读写权限

3. **配置文件格式错误**
   ```
   错误：配置文件格式错误
   ```
   解决：检查 TOML 语法，确保字符串使用引号，数组使用方括号

### 调试模式

如需查看详细日志，可以修改日志级别：

```python
# 在代码中设置调试级别
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## 📄 许可证

本项目基于开源许可证发布。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 📞 支持

如果您在使用过程中遇到问题，请：

1. 查看本 README 文件的故障排除部分
2. 检查项目的 Issue 页面
3. 提交新的 Issue 描述您的问题

---

**FTP2Python** - 让文件共享变得简单！

- 项目完全采用 vibe coding，如有不满还请寻找其它项目