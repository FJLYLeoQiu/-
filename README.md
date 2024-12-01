# Time-Play 音乐播放器 v2.02

一个基于时间调度的智能音乐播放系统，支持工作日过滤和中国节假日识别。

## 功能特点

- 基于时间的音乐播放调度
- 支持工作日过滤
- 支持自定义大小周设置
  - 可配置奇数周双休/单休
  - 可配置偶数周双休/单休
  - 可配置单休周六是否上班
- 支持中国节假日识别
- Web管理界面
- 系统日志记录
- 系统服务集成

## 系统要求

- Ubuntu Linux
- Python 3.10 或更高版本
- 系统音频支持（ALSA）
- pygame 库（用于音频播放）

## 安装说明

1. 安装系统依赖：
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-pygame
```

2. 运行安装脚本：
```bash
sudo ./manage.sh install
```

## 使用说明

### 命令行管理

使用统一的管理脚本 `manage.sh` 进行所有操作：

```bash
sudo ./manage.sh [命令]
```

可用命令：
- `install`     : 安装应用
- `uninstall`   : 卸载应用
- `start`       : 启动服务
- `stop`        : 停止服务
- `restart`     : 重启服务
- `status`      : 查看服务状态
- `logs`        : 查看日志
- `clear-logs`  : 清理日志
- `calendar`    : 查看节假日数据版本
- `help`        : 显示帮助信息

示例：
```bash
# 安装应用
sudo ./manage.sh install

# 启动服务
sudo ./manage.sh start

# 查看服务状态
sudo ./manage.sh status

# 查看实时日志
sudo ./manage.sh logs
```

### Web 界面

访问 http://localhost:5000 使用 Web 管理界面：

- 查看任务状态
- 管理播放计划
- 查看系统日志
- 检查节假日信息

## 配置说明

### 大小周设置

在Web界面的系统维护部分，你可以配置：

1. 奇数周设置：选择奇数周是双休还是单休
2. 偶数周设置：选择偶数周是双休还是单休
3. 单休设置：选择单休周的周六是否需要上班

配置会自动保存，并立即生效。

### 音乐文件

- 位置：`/opt/time-play/music/`
- 支持格式：MP3、WAV
- 建议：使用相对路径配置音乐文件

### 播放计划

在 Web 界面或直接编辑 `schedule.json`：

```json
{
  "tasks": [
    {
      "name": "早间音乐",
      "time": "09:00",
      "music": "morning.mp3",
      "workday_only": true
    }
  ]
}
```

### 定时任务

在Web界面添加定时任务时，可以：

1. 设置播放时间
2. 选择音乐文件
3. 选择是否仅在工作日播放（会根据大小周设置和节假日自动判断）

### 日志文件

- 系统日志：`/var/log/syslog`
- 应用日志：`/opt/time-play/logs/time-play.log`
- 查看日志：`sudo ./manage.sh logs`
- 清理日志：`sudo ./manage.sh clear-logs`

## 音频配置说明

系统使用 ALSA 和 pygame 进行音频播放。如果遇到音频问题，请检查：

1. 确保系统音量未静音：
```bash
# 检查音频设备
aplay -l

# 调整音量（可选）
alsamixer
```

2. 确保当前用户在 audio 组中：
```bash
# 检查当前用户组
groups

# 如果需要，将用户添加到 audio 组
sudo usermod -a -G audio $USER
```

3. 测试音频系统：
```bash
# 使用提供的测试脚本
python3 test_audio.py
```

如果测试失败，请检查系统日志获取详细错误信息。

## 故障排除

### 1. 服务无法启动

检查：
```bash
sudo ./manage.sh status
journalctl -u time-play
```

### 2. 音乐不播放

确认：
- 音频设备正常工作
- 音乐文件存在且格式正确
- 系统音量已打开

### 3. 节假日判断异常

运行：
```bash
sudo ./manage.sh calendar
```
检查中国节假日数据是否最新

## 开发说明

### 项目结构

```
/opt/time-play/
├── play_music.py    # 主程序
├── manage.sh      # 统一管理脚本
├── schedule.json    # 任务配置
├── requirements.txt # Python 依赖
├── templates/       # Web 模板
├── music/          # 音乐文件
└── logs/           # 日志文件
```

### 依赖管理

主要依赖：
- Flask：Web 框架
- Pygame：音频播放
- chinese_calendar：节假日支持

## 技术支持

如遇问题：
1. 检查系统日志：`sudo ./manage.sh logs`
2. 查看服务状态：`sudo ./manage.sh status`
3. 尝试重启服务：`sudo ./manage.sh restart`

## 许可说明

本项目采用 MIT 许可证。

## 更新日志

### 2.02 (2024年11月)
- 改进安装脚本的健壮性
- 优化服务安装流程
- 修复权限问题
- 改进错误处理

### 2.01 (2024年11月)
- 整合部署和管理脚本为统一的 manage.sh
- 改进错误处理和日志管理
- 增强服务管理功能
- 优化安装流程
- 完善文档说明

### 1.0.0
- 初始发布
- 完整的任务调度系统
- Web 管理界面
- 系统服务集成
- DEB 包支持

### 服务管理

除了使用 `manage.sh` 脚本，你还可以使用新的 [manage.sh](cci:7://file:///opt/time-play/manage.sh:0:0-0:0) 脚本进行服务管理：

```bash
# 创建系统服务
sudo ./manage.sh create

# 设置开机自启动
sudo ./manage.sh enable

# 启动服务
sudo ./manage.sh start

# 停止服务
sudo ./manage.sh stop

# 重启服务
sudo ./manage.sh restart

# 查看服务状态
sudo ./manage.sh status
---
*最后更新：2024年11月*
