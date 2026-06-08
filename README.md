# QQ Chat History Reader
QQ聊天记录读取器

## 简介 | Introduction

QQ Chat History Reader 是一款轻量级工具，用于读取 Symbian 版 QQ 客户端的聊天记录。

QQ Chat History Reader is a lightweight tool for reading chat history from Symbian-version QQ clients.

## 功能特点 | Features

- 支持 Symbian 版 QQ 聊天记录文件 | Support Symbian-version QQ chat history files
- 在 WebView 窗口中展示聊天记录 | Display chat history in WebView window
- 多主题支持：经典 Symbian QQ 主题、现代 QQ 主题、微信主题 | Multiple themes: Classic Symbian QQ, Modern QQ, and WeChat themes

## 使用方法 | How to Use

1. 安装requirements.txt里的依赖 | Install all dependencies.
```bash
pip install -r requirements.txt
```
2. 运行main.py | run main.py
```bash
python main.py
```

## 项目结构 | Project Structure

```
qq-chat-reader/
├── main.py              # 应用入口 / Application entry point
├── server.py            # Flask 服务器 / Flask server
├── models.py            # 数据模型 / Data models
├── decode_avatar.py     # 头像解码 / Avatar decoder
├── parser/              # 聊天记录解析器 / Chat history parser
├── assets/              # 静态资源 / Static assets
├── web/                 # 前端文件 / Frontend files
│   └── themes/          # 主题样式 / Theme styles
└── requirements.txt     # 项目依赖 / Project dependencies
```

## 界面预览 | Interface Preview

应用启动后显示简洁的侧边栏，包含聊天会话列表。用户可点击会话查看聊天记录，支持以下三种主题风格：

After launching, the app displays a sidebar with a list of conversations. Users can click on a conversation to view the chat history. Three theme styles are available for selection:

- **经典 Symbian QQ 主题 / Classic Symbian QQ Theme** - 还原 Symbian 版 QQ 的原始界面风格 / Restores the original interface style of Symbian QQ
- **现代 QQ 主题 / Modern QQ Theme** - 采用现代 QQ 的设计语言 / Adopts modern QQ design language
- **微信主题 / WeChat Theme** - 类似微信的简洁界面 / Clean interface similar to WeChat


## 许可证 | License

本项目基于 MIT 许可证开源。

This project is open source under the MIT License.

---

**腾讯 QQ 表情资源声明 / Tencent QQ Face Assets Notice**

所有表情资源均来自腾讯官方，版权归腾讯公司所有。仅供学习交流使用，请勿用于商业用途。

All QQ face/emoticon assets are from Tencent's official sources and are copyrighted by Tencent. They are provided for learning and communication purposes only. Please do not use them for commercial purposes.
