#!/bin/bash

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 项目路径
PROJECT_PATH="/opt/time-play"
VENV_PATH="$PROJECT_PATH/.venv"
SERVICE_NAME="timeplay"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

# 创建服务文件
create_service() {
    cat > $SERVICE_FILE << EOL
[Unit]
Description=Time Play Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_PATH
Environment=PATH=$VENV_PATH/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=$PROJECT_PATH
Environment=LC_ALL=zh_CN.UTF-8
Environment=LANG=zh_CN.UTF-8
ExecStart=$VENV_PATH/bin/python3 $PROJECT_PATH/play_music.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

    # 重新加载systemd配置
    systemctl daemon-reload
    echo "服务文件已创建: $SERVICE_FILE"
}

# 启用服务自启动
enable_service() {
    systemctl enable $SERVICE_NAME
    echo "服务已设置为开机自启动"
}

# 启动服务
start_service() {
    systemctl start $SERVICE_NAME
    echo "服务已启动"
}

# 停止服务
stop_service() {
    systemctl stop $SERVICE_NAME
    echo "服务已停止"
}

# 重启服务
restart_service() {
    systemctl restart $SERVICE_NAME
    echo "服务已重启"
}

# 检查服务状态
check_status() {
    systemctl status $SERVICE_NAME
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 {create|enable|start|stop|restart|status}"
    echo "  create  - 创建服务文件"
    echo "  enable  - 设置服务开机自启动"
    echo "  start   - 启动服务"
    echo "  stop    - 停止服务"
    echo "  restart - 重启服务"
    echo "  status  - 查看服务状态"
}

# 主函数
case "$1" in
    create)
        create_service
        ;;
    enable)
        enable_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        check_status
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0
