#!/bin/bash

# Time-Play 管理脚本 v2.01
# 整合了部署和管理功能

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
APP_NAME="time-play"
APP_DIR="/opt/time-play"
VENV_DIR="$APP_DIR/venv"
PYTHON_VERSION="3.10"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
LOG_FILE="$APP_DIR/logs/time-play.log"
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"

# 确保以 root 权限运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
        exit 1
    fi
}

# 检查 Python 版本
check_python_version() {
    echo -e "${BLUE}[INFO] 检查 Python 版本...${NC}"
    if command -v python$PYTHON_VERSION &>/dev/null; then
        echo -e "${GREEN}[OK] Python $PYTHON_VERSION 已安装${NC}"
    else
        echo -e "${RED}[ERROR] 未找到 Python $PYTHON_VERSION${NC}"
        echo -e "${YELLOW}[INFO] 尝试安装 Python $PYTHON_VERSION...${NC}"
        apt-get update
        apt-get install -y python$PYTHON_VERSION python$PYTHON_VERSION-venv
        if [ $? -ne 0 ]; then
            echo -e "${RED}[ERROR] Python 安装失败${NC}"
            exit 1
        fi
    fi
}

# 创建虚拟环境
create_venv() {
    echo -e "${BLUE}[INFO] 创建虚拟环境...${NC}"
    if [ ! -d "$VENV_DIR" ]; then
        python$PYTHON_VERSION -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo -e "${RED}[ERROR] 虚拟环境创建失败${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}[OK] 虚拟环境已就绪${NC}"
}

# 安装依赖
install_dependencies() {
    echo -e "${BLUE}[INFO] 安装依赖...${NC}"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] 依赖安装失败${NC}"
        exit 1
    fi
    deactivate
    echo -e "${GREEN}[OK] 依赖安装完成${NC}"
}

# 创建系统服务
create_service() {
    echo -e "${BLUE}[INFO] 创建系统服务...${NC}"
    cat > "$SERVICE_FILE" << EOL
[Unit]
Description=Time-Play Music Player
After=network.target sound.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_DIR/bin/python $APP_DIR/play_music.py
Restart=on-failure
RestartSec=5
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOL

    chmod 644 "$SERVICE_FILE"
    systemctl daemon-reload
    echo -e "${GREEN}[OK] 系统服务创建完成${NC}"
}

# 创建日志目录
setup_logging() {
    echo -e "${BLUE}[INFO] 设置日志...${NC}"
    mkdir -p "$APP_DIR/logs"
    touch "$LOG_FILE"
    chown -R $SUDO_USER:$SUDO_USER "$APP_DIR/logs"
    echo -e "${GREEN}[OK] 日志设置完成${NC}"
}

# 安装应用
install() {
    echo -e "${BLUE}[INFO] 开始安装 Time-Play...${NC}"
    check_root
    check_python_version
    create_venv
    install_dependencies
    setup_logging
    create_service
    echo -e "${GREEN}[SUCCESS] Time-Play 安装完成！${NC}"
}

# 卸载应用
uninstall() {
    echo -e "${YELLOW}[WARN] 开始卸载 Time-Play...${NC}"
    check_root
    
    # 停止并删除服务
    systemctl stop $APP_NAME 2>/dev/null
    systemctl disable $APP_NAME 2>/dev/null
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload
    
    # 删除虚拟环境
    rm -rf "$VENV_DIR"
    
    echo -e "${GREEN}[SUCCESS] Time-Play 卸载完成${NC}"
    echo -e "${YELLOW}注意: 应用目录 $APP_DIR 未被删除，如需完全删除请手动执行:${NC}"
    echo -e "${YELLOW}rm -rf $APP_DIR${NC}"
}

# 启动服务
start() {
    echo -e "${BLUE}[INFO] 启动 Time-Play 服务...${NC}"
    systemctl start $APP_NAME
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SUCCESS] 服务已启动${NC}"
    else
        echo -e "${RED}[ERROR] 服务启动失败${NC}"
        echo -e "${YELLOW}查看详细错误: journalctl -u $APP_NAME${NC}"
    fi
}

# 停止服务
stop() {
    echo -e "${BLUE}[INFO] 停止 Time-Play 服务...${NC}"
    systemctl stop $APP_NAME
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SUCCESS] 服务已停止${NC}"
    else
        echo -e "${RED}[ERROR] 服务停止失败${NC}"
    fi
}

# 重启服务
restart() {
    echo -e "${BLUE}[INFO] 重启 Time-Play 服务...${NC}"
    systemctl restart $APP_NAME
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SUCCESS] 服务已重启${NC}"
    else
        echo -e "${RED}[ERROR] 服务重启失败${NC}"
        echo -e "${YELLOW}查看详细错误: journalctl -u $APP_NAME${NC}"
    fi
}

# 查看服务状态
status() {
    systemctl status $APP_NAME
}

# 查看日志
logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}[ERROR] 日志文件不存在${NC}"
    fi
}

# 清理日志
clear_logs() {
    echo -e "${YELLOW}[WARN] 清理日志文件...${NC}"
    if [ -f "$LOG_FILE" ]; then
        echo "" > "$LOG_FILE"
        echo -e "${GREEN}[SUCCESS] 日志已清理${NC}"
    else
        echo -e "${RED}[ERROR] 日志文件不存在${NC}"
    fi
}

# 检查中国节假日数据版本
calendar_version() {
    source "$VENV_DIR/bin/activate"
    python - << EOF
import chinese_calendar
print(f"中国节假日数据版本: {chinese_calendar.__version__}")
try:
    years = chinese_calendar.get_available_years()
    print(f"支持年份范围: {min(years)} - {max(years)}")
except Exception as e:
    print(f"获取年份范围失败: {e}")
EOF
    deactivate
}

# 更新服务配置
update_service() {
    echo -e "${BLUE}[INFO] 更新服务配置...${NC}"
    
    # 检查新的服务配置文件是否存在
    if [ ! -f "$APP_DIR/time-play.service.new" ]; then
        echo -e "${RED}[ERROR] 新的服务配置文件不存在${NC}"
        return 1
    fi
    
    # 复制新的服务配置文件
    cp "$APP_DIR/time-play.service.new" "$SERVICE_FILE"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] 更新服务配置失败${NC}"
        return 1
    fi
    
    # 重新加载systemd配置
    systemctl daemon-reload
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] 重新加载systemd配置失败${NC}"
        return 1
    fi
    
    echo -e "${GREEN}[SUCCESS] 服务配置已更新${NC}"
    return 0
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}Time-Play 管理脚本${NC}"
    echo
    echo "用法: $0 [命令]"
    echo
    echo "命令:"
    echo "  install        安装服务"
    echo "  uninstall      卸载服务"
    echo "  start          启动服务"
    echo "  stop           停止服务"
    echo "  restart        重启服务"
    echo "  status         查看服务状态"
    echo "  logs           查看日志"
    echo "  clear-logs     清理日志"
    echo "  calendar-version 查看节假日数据版本"
    echo "  update-service 更新服务配置"
    echo "  help           显示此帮助信息"
}

# 主函数
main() {
    check_root
    
    case "$1" in
        "install")
            install
            ;;
        "uninstall")
            uninstall
            ;;
        "start")
            start
            ;;
        "stop")
            stop
            ;;
        "restart")
            restart
            ;;
        "status")
            status
            ;;
        "logs")
            logs
            ;;
        "clear-logs")
            clear_logs
            ;;
        "calendar-version")
            calendar_version
            ;;
        "update-service")
            update_service
            ;;
        *)
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
