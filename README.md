# FTP2Python

一个简单易用的轻量级 FTP 服务器，支持图形界面和命令行两种使用方式。

## 🌟 主要特性

- **双模式运行**：支持图形界面（GUI）和命令行（CLI）两种模式
- **TOML 配置**：使用现代化的 TOML 格式配置文件
- **多用户支持**：支持配置多个用户账户，每个用户可设置独立的权限和主目录
- **国际化支持**：内置中文和英文界面，支持语言切换
- **实时日志**：提供详细的服务器运行日志，支持日志保存
- **可执行文件**：支持打包为独立的 exe 可执行文件，无需安装 Python 环境
- **自动配置**：首次运行时自动创建默认配置文件
- **网络检测**：自动检测本机 IP 地址，方便客户端连接

## 📋 系统要求

- Python 3.11+ （如使用源码运行）
- Windows/Linux/macOS
- 网络端口访问权限

## 🚀 快速开始

### 方式一：使用可执行文件（推荐）

1. 下载最新版本的 `ftp2python.exe`
2. 双击运行，将自动启动图形界面
3. 在界面中配置服务器设置和用户账户
4. 点击"启动服务器"按钮

### 方式二：从源码运行

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd ftp2python
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **启动图形界面**
   ```bash
   python __init__.py
   ```

4. **或启动命令行模式**
   ```bash
   python __init__.py --cli
   ```

## 🎯 使用方法

### 图形界面模式

启动后将显示友好的图形界面，包含以下功能：

- **服务器配置**：设置端口、监听地址、最大连接数等
- **用户管理**：添加、编辑、删除用户账户
- **实时日志**：查看服务器运行状态和连接日志
- **语言切换**：支持中文/英文界面切换

### 命令行模式

```bash
# 基本启动
python __init__.py --cli

# 指定配置文件
python __init__.py --cli -c my_config.toml

# 指定共享目录
python __init__.py --cli -s /path/to/share

# 指定端口
python __init__.py --cli -p 2122

# 使用英文界面
python __init__.py --cli -l en_US
```

## ⚙️ 配置文件

项目使用 TOML 格式的配置文件（默认为 `config.toml`）：

```toml
port = 2121
listen = "0.0.0.0"
max_cons = 256
max_cons_per_ip = 10
banner = "欢迎使用 FTP 服务器"
language = "zh_CN"

[[users]]
username = "user"
password = "123456"
perm = "elradfmw"
home = "./shared"

[[users]]
username = "admin"
password = "admin123"
perm = "elradfmw"
home = "./admin_files"
```

### 配置项说明

- `port`: FTP 服务器端口（默认 2121）
- `listen`: 监听地址（默认 "0.0.0.0" 表示所有网卡）
- `max_cons`: 最大连接数
- `max_cons_per_ip`: 每个 IP 的最大连接数
- `banner`: 连接时显示的欢迎信息
- `language`: 界面语言（zh_CN 或 en_US）

### 用户权限说明

`perm` 字段定义用户权限，可包含以下字符：

- `e`: 更改目录
- `l`: 列出文件
- `r`: 从服务器下载文件
- `a`: 向服务器上传文件
- `d`: 删除文件
- `f`: 重命名文件
- `m`: 创建目录
- `w`: 写入权限

## 🔧 开发和打包

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements.txt
pip install pyinstaller

# 运行测试
python __init__.py
```

### 打包为可执行文件

项目提供了三个 PyInstaller 配置文件：

```bash
# 标准打包（启用 UPX 压缩）
pyinstaller .\ftp2python.spec

# 禁用 UPX 压缩的打包（兼容性更好）
pyinstaller .\ftp2python-disable-upx.spec

# 启用终端的打包（调试用）
pyinstaller .\ftp2python-debug.spec
```

打包后的可执行文件位于 `dist/` 目录中。

## 📁 项目结构

```
ftp2python/
├── __init__.py              # 主入口文件
├── requirements.txt         # 项目依赖
├── ftp2python.spec         # PyInstaller 配置（启用 UPX）
├── ftp2python-disable-upx.spec  # PyInstaller 配置（禁用 UPX）
├── core/                   # 核心功能模块
│   ├── config.py          # 配置文件管理
│   ├── server_manager.py  # FTP 服务器管理
│   ├── user_manager.py    # 用户管理
│   ├── logger.py          # 日志系统
│   ├── i18n.py           # 国际化支持
│   └── locales/          # 语言文件
│       ├── zh_CN.toml    # 中文翻译
│       └── en_US.toml    # 英文翻译
└── gui/                   # 图形界面模块
    └── main.py           # GUI 主程序
```

## 🌐 网络配置

### 防火墙设置

确保以下端口在防火墙中开放：
- FTP 控制端口（默认 2121）
- FTP 数据端口（如果配置了被动模式端口范围）

### 路由器设置

如需外网访问，请在路由器中设置端口转发：
- 将外网端口转发到运行 FTP 服务器的内网 IP 和端口

## 🐛 常见问题

### Q: 无法连接到 FTP 服务器
A: 检查防火墙设置，确保 FTP 端口已开放。检查服务器是否正常启动。

### Q: 上传文件失败
A: 检查用户权限配置，确保用户具有写入权限（`perm` 包含 `a` 和 `w`）。

### Q: 中文文件名显示乱码
A: 确保 FTP 客户端支持 UTF-8 编码，或使用支持中文的 FTP 客户端。

### Q: 可执行文件启动失败
A: 尝试使用 `ftp2python-disable-upx.spec` 重新打包，或直接使用源码运行。

## 📄 许可证

本项目采用开源许可证，具体许可证信息请查看项目根目录的 LICENSE 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 📞 支持

如果您在使用过程中遇到问题，请：
1. 查看本文档的常见问题部分
2. 在项目 Issues 页面搜索相关问题
3. 提交新的 Issue 描述您的问题

---

**FTP2Python** - 让文件共享变得简单！

- 项目完全采用 vibe coding，如有不满还请寻找其它项目
