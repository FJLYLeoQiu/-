import os
import sys
import time
import json
import datetime
import logging
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import chinese_calendar
import pygame
import pkg_resources
from collections import deque
import schedule
import numpy as np
import locale

# 初始化日志记录器
logger = logging.getLogger('time-play')
logger.setLevel(logging.INFO)

# 创建文件处理器
LOG_DIR = os.path.join(os.path.expanduser('~'), '.time-play', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)

# 配置文件路径
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
SCHEDULE_FILE = os.path.join(CONFIG_DIR, 'schedule.json')
os.makedirs(CONFIG_DIR, mode=0o755, exist_ok=True)

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# 日志处理器
class MemoryHandler(logging.Handler):
    def emit(self, record):
        try:
            # 格式化日志消息
            msg = self.format(record)
            # 添加到缓冲区
            log_buffer.append(msg)
            # 保持最近1000条日志
            if len(log_buffer) > 1000:
                log_buffer.pop(0)
        except Exception:
            self.handleError(record)

# 配置日志处理器
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
memory_handler = MemoryHandler()
memory_handler.setFormatter(formatter)
logger.addHandler(memory_handler)

# 创建一个环形缓冲区来存储最近的日志
log_buffer = deque(maxlen=1000)

def get_calendar_version():
    """获取日历版本信息"""
    try:
        version = pkg_resources.get_distribution('chinese-calendar').version
        
        # 动态获取支持的年份范围
        min_year = min(date.year for date in chinese_calendar.holidays.keys())
        max_year = max(date.year for date in chinese_calendar.holidays.keys())
        year_range = f'{min_year}-{max_year}'
        
        return {'version': version, 'year_range': year_range}
    except Exception as e:
        logger.error(f"获取日历版本信息失败: {str(e)}")
        return {'version': '未知', 'year_range': '未知'}

def check_calendar_update():
    """检查并更新节假日数据"""
    try:
        # 确保chinese_calendar模块已正确加载
        if not hasattr(chinese_calendar, 'holidays'):
            logger.error("chinese_calendar模块未正确加载")
            return False
            
        version_info = get_calendar_version()
        current_year = datetime.datetime.now().year
        
        # 检查是否包含当前年份的数据
        if version_info['year_range'] != '未知':
            year_range = version_info['year_range'].split('-')
            if len(year_range) == 2:
                start_year, end_year = map(int, year_range)
                if not (start_year <= current_year <= end_year):
                    logger.error(f"节假日数据不包含当前年份 {current_year}")
                    return False
        
        logger.info(f"节假日数据检查成功: 版本 {version_info['version']}, 年份范围 {version_info['year_range']}")
        return True
    except Exception as e:
        logger.error(f"检查节假日数据失败: {str(e)}")
        return False

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# 全局变量
MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'music')
schedule_thread = None

# 确保必要的目录存在
os.makedirs(os.path.dirname(MUSIC_DIR), exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

# 初始加载日志
def load_logs():
    """从日志文件加载最近的日志"""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                # 读取最后1000行
                lines = f.readlines()[-1000:]
                for line in lines:
                    line = line.strip()
                    if line:
                        log_buffer.append(line)
    except Exception as e:
        print(f"加载日志失败: {str(e)}")

load_logs()

def create_app():
    """创建并初始化Flask应用"""
    with app.app_context():
        logger.info("正在初始化应用...")
        
        # 确保配置目录和文件存在
        os.makedirs(CONFIG_DIR, mode=0o755, exist_ok=True)
        if not os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            logger.info(f"创建空的定时任务文件: {SCHEDULE_FILE}")
        
        # 初始化pygame
        try:
            pygame.mixer.quit()
            pygame.mixer.init()
            logger.info("音频系统初始化成功")
        except Exception as e:
            logger.warning(f"pygame音频初始化失败，将使用备用播放器: {str(e)}")
        
        # 启动后台线程
        start_background_threads()
        logger.info("应用初始化完成")
    
    return app

def get_task_overview():
    """获取任务概览信息"""
    try:
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        schedule = load_schedule()
        
        # 获取今日任务
        today_tasks = []
        next_task = None
        next_task_time = None
        
        # 按时间排序的任务列表
        sorted_times = sorted(schedule.keys())
        
        # 检查日志中的任务执行记录
        executed_tasks = set()
        for line in list(log_buffer):
            if "执行定时任务:" in line:
                # 从日志中提取时间和文件名
                parts = line.split(" - ")
                if len(parts) >= 2:
                    time_str = parts[1].strip()
                    executed_tasks.add(time_str)
        
        for time_str in sorted_times:
            task = schedule[time_str]
            task_info = {
                'time': time_str,
                'music_file': task['music_file'],
                'workday_only': task.get('workday_only', False)
            }
            
            # 检查是否是今日任务
            if task.get('workday_only', False) and not workday(datetime.datetime.now()):
                continue
            
            # 根据日志记录和当前时间判断任务状态
            if time_str in executed_tasks:
                task_info['status'] = '已完成'
            elif time_str < current_time:
                if task.get('workday_only', False) and not workday(datetime.datetime.now()):
                    task_info['status'] = '已跳过'
                else:
                    task_info['status'] = '已过期'
            else:
                if task.get('workday_only', False) and not workday(datetime.datetime.now()):
                    task_info['status'] = '将跳过'
                else:
                    task_info['status'] = '待执行'
            
            today_tasks.append(task_info)
            
            # 查找下一个要执行的任务
            if time_str > current_time and (next_task is None or time_str < next_task_time):
                if not task.get('workday_only', False) or workday(datetime.datetime.now()):
                    next_task = task_info.copy()
                    next_task_time = time_str
                    
                    # 计算倒计时和执行日期
                    task_time = datetime.datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M")
                    time_diff = task_time - now
                    
                    # 如果任务时间小于当前时间，说明是明天的任务
                    if task_time < now:
                        task_time = task_time + datetime.timedelta(days=1)
                        time_diff = task_time - now
                    
                    # 格式化执行日期
                    next_task['execute_date'] = task_time.strftime("%Y-%m-%d")
                    next_task['execute_time'] = task_time.strftime("%H:%M")
                    
                    # 计算倒计时
                    hours = int(time_diff.total_seconds() // 3600)
                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                    next_task['countdown'] = f"{hours}小时{minutes}分钟"
        
        return {
            'today_tasks': today_tasks,
            'next_task': next_task
        }
    except Exception as e:
        logger.error(f"获取任务概览失败: {str(e)}")
        return {
            'today_tasks': [],
            'next_task': None
        }

def load_schedule():
    """加载定时任务"""
    try:
        if os.path.exists(SCHEDULE_FILE):
            # 以二进制模式读取文件
            with open(SCHEDULE_FILE, 'rb') as f:
                content = f.read().decode('utf-8')
                return json.loads(content)
    except Exception as e:
        logger.error(f"加载定时任务失败: {str(e)}")
    return {}

def save_schedule(schedule):
    """保存定时任务"""
    try:
        # 确保父目录存在
        os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
        
        # 确保文件存在
        if not os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False)

        # 使用临时文件来保存，以避免写入过程中的文件损坏
        temp_file = SCHEDULE_FILE + '.tmp'
        
        # 将schedule转换为JSON字符串，确保使用UTF-8编码
        json_str = json.dumps(schedule, ensure_ascii=False, indent=2)
        
        # 以二进制模式写入文件
        with open(temp_file, 'wb') as f:
            f.write(json_str.encode('utf-8'))
        
        # 替换原文件
        os.replace(temp_file, SCHEDULE_FILE)
        
        logger.info("定时任务保存成功")
        return True, "保存成功"
    except Exception as e:
        error_msg = f"保存定时任务失败: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

# 用户类
class User(UserMixin):
    def __init__(self, id, username, name):
        self.id = username  # 使用username作为id
        self.username = username
        self.name = name

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'

@login_manager.user_loader
def load_user(user_id):
    try:
        users_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
            if user_id in users:
                return User(user_id, user_id, users[user_id]['name'])
    except Exception as e:
        app.logger.error(f"加载用户时出错: {str(e)}")
    return None

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            users_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                app.logger.info(f"尝试登录用户: {username}")
                if username in users:
                    stored_hash = users[username]['password']
                    if check_password_hash(stored_hash, password):
                        user = User(username, username, users[username]['name'])
                        login_user(user)
                        app.logger.info("登录成功")
                        return redirect(url_for('index'))
                app.logger.info("验证失败")
                return render_template('login.html', error='用户名或密码错误')
        except Exception as e:
            app.logger.error(f"登录时出错: {str(e)}")
            return render_template('login.html', error='系统错误，请稍后重试')
    
    return render_template('login.html')

# 注销路由
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 修改密码路由
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证新密码
        if new_password != confirm_password:
            return render_template('change_password.html', error='新密码和确认密码不匹配')
        
        if len(new_password) < 6:
            return render_template('change_password.html', error='新密码长度不能少于6个字符')
            
        try:
            users_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            # 验证当前密码是否正确
            stored_hash = users[current_user.id]['password']
            if not check_password_hash(stored_hash, current_password):
                return render_template('change_password.html', error='当前密码错误')
            
            # 更新密码
            users[current_user.id]['password'] = generate_password_hash(new_password)
            
            # 保存更改
            if save_users(users):
                flash('密码修改成功')
                return redirect(url_for('index'))
            else:
                return render_template('change_password.html', error='系统错误，请稍后重试')
                
        except Exception as e:
            app.logger.error(f"修改密码时出错: {str(e)}")
            return render_template('change_password.html', error='系统错误，请稍后重试')
    
    return render_template('change_password.html')

# 主页路由
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/music')
@login_required
def list_music():
    """列出所有音乐文件"""
    try:
        # 确保返回的文件名是UTF-8编码
        files = [f.decode('utf-8') if isinstance(f, bytes) else f 
                for f in os.listdir(MUSIC_DIR) 
                if f.lower().endswith(('.mp3', '.wav'))]
        return jsonify(files)
    except Exception as e:
        error_msg = f"列出音乐文件错误: {e}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 500

@app.route('/api/play', methods=['POST'])
@login_required
def play():
    """播放音乐"""
    try:
        data = request.json
        play_music(os.path.join(MUSIC_DIR, data.get('music_file')))
        return jsonify({'status': 'success'})
    except Exception as e:
        error_msg = f"播放音乐错误: {e}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 500

@app.route('/api/stop', methods=['POST'])
@login_required
def stop():
    """停止播放"""
    try:
        stop_music()
        return jsonify({'status': 'success'})
    except Exception as e:
        error_msg = f"停止播放错误: {e}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 500

@app.route('/api/schedule', methods=['GET', 'POST'])
@login_required
def manage_schedule():
    """管理定时任务"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'error': '无效的请求数据'}), 400

            time = data.get('time')
            music_file = data.get('music_file')
            workday_only = data.get('workday_only', False)

            if not time or not music_file:
                return jsonify({'status': 'error', 'error': '缺少必要的参数'}), 400

            # 加载现有的时间表
            schedule = load_schedule()
            
            # 添加新任务
            schedule[time] = {
                'music_file': music_file,
                'workday_only': workday_only
            }
            
            # 保存时间表
            save_schedule(schedule)
            logger.info("定时任务保存成功")
            logger.info(f"添加定时任务: {time} - {music_file} ({'仅工作日' if workday_only else '每天'})")
            
            # 重启定时任务线程
            check_and_restart_schedule_thread()
            
            return jsonify({'status': 'success'})
        except Exception as e:
            logger.error(f"保存定时任务失败: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    elif request.method == 'GET':
        try:
            schedule = load_schedule()
            return jsonify(schedule)
        except Exception as e:
            logger.error(f"获取定时任务失败: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/schedule/<time>', methods=['DELETE'])
@login_required
def delete_schedule(time):
    """删除定时任务"""
    try:
        schedule = load_schedule()
        
        if time in schedule:
            task = schedule[time]
            del schedule[time]
            save_schedule(schedule)
            logger.info("定时任务保存成功")
            logger.info(f"删除定时任务: {time} - {task['music_file']} ({'仅工作日' if task.get('workday_only') else '每天'})")
            
            # 重启定时任务线程
            check_and_restart_schedule_thread()
            
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'error': '指定的时间不存在'}), 404
    except Exception as e:
        logger.error(f"删除定时任务失败: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

def get_week_schedule():
    """获取周日程配置"""
    config = load_config()
    return config.get('week_schedule', {
        "odd_week_rest": True,
        "even_week_rest": False,
        "saturday_work": True
    })

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
    
    # 默认配置
    return {
        "week_schedule": {
            "odd_week_rest": True,
            "even_week_rest": False,
            "saturday_work": True
        },
        "volume": 80  # 添加默认音量设置
    }

def save_config(config):
    """保存配置文件"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {str(e)}")
        return False

@app.route('/api/calendar-version')
@login_required
def get_calendar_version_api():
    """获取日历版本API"""
    try:
        version_info = get_calendar_version()
        return jsonify(version_info)
    except Exception as e:
        logger.error(f"获取日历版本失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/task-overview')
@login_required
def task_overview():
    """获取任务概览的API端点"""
    try:
        overview = get_task_overview()
        return jsonify(overview)
    except Exception as e:
        logger.error(f"任务概览API错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
@login_required
def get_logs():
    """获取运行日志的API端点"""
    try:
        # 确保日志文件存在
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                pass
            
        # 返回内存中的日志缓存
        logs = list(log_buffer)
        logger.debug(f"返回日志条数: {len(logs)}")
        return jsonify({"logs": logs})
    except Exception as e:
        error_msg = f"获取日志失败: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

def clear_logs():
    """清除所有日志"""
    try:
        # 清除日志文件
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        # 清除内存中的日志缓存
        log_buffer.clear()
        logger.info('日志已清除')
        return True
    except Exception as e:
        logger.error(f"清除日志失败: {str(e)}")
        return False

@app.route('/api/clear-logs', methods=['POST'])
@login_required
def clear_logs_endpoint():
    """清除日志的API端点"""
    if clear_logs():
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': '清除日志失败'}), 500

@app.route('/api/week-schedule', methods=['GET'])
@login_required
def get_week_schedule_api():
    """获取周设置"""
    try:
        config = load_config()
        return jsonify(config['week_schedule'])
    except Exception as e:
        logger.error(f"获取周设置失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/week-schedule', methods=['POST'])
@login_required
def update_week_schedule_api():
    """更新周设置"""
    try:
        if not request.is_json:
            return jsonify({'error': '无效的请求格式'}), 400
            
        data = request.get_json()
        if data is None:
            return jsonify({'error': '无效的JSON数据'}), 400
            
        config = load_config()
        config['week_schedule'] = {
            'odd_week_rest': bool(data.get('odd_week_rest', True)),
            'even_week_rest': bool(data.get('even_week_rest', False)),
            'saturday_work': bool(data.get('saturday_work', True))
        }
        
        if save_config(config):
            logger.info(f"更新周设置成功: {config['week_schedule']}")
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': '保存配置失败'}), 500
    except Exception as e:
        logger.error(f"更新周设置失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-audio', methods=['POST'])
@login_required
def test_audio():
    """测试音频系统"""
    try:
        # 生成一个简单的测试音频
        sample_rate = 44100
        duration = 1.0  # 1秒
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 440 * t)  # 440Hz
        
        # 保存为临时文件
        test_file = os.path.join(MUSIC_DIR, 'test.wav')
        try:
            import scipy.io.wavfile as wav
            wav.write(test_file, sample_rate, test_signal)
        except ImportError:
            # 如果没有 scipy，使用 pygame 生成音频
            pygame.mixer.Sound(test_signal.astype(np.int16)).save(test_file)
        
        # 播放测试音频
        success = play_music(test_file)
        
        # 清理临时文件
        try:
            os.remove(test_file)
        except:
            pass
        
        if success:
            return jsonify({'status': 'success', 'message': '音频测试成功'})
        else:
            return jsonify({'status': 'error', 'message': '音频播放失败'})
    except Exception as e:
        logger.error(f"音频测试失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_next_task():
    """获取下一个要执行的任务"""
    try:
        current_time = datetime.datetime.now()
        schedule = load_schedule()
        
        # 将所有时间转换为今天的日期时间对象进行比较
        next_task = None
        next_task_time = None
        
        for time_str, task in schedule.items():
            # 解析时间
            task_time = datetime.datetime.strptime(time_str, '%H:%M').time()
            task_datetime = datetime.datetime.combine(current_time.date(), task_time)
            
            # 如果时间已过，则看明天的这个时间
            if task_datetime <= current_time:
                task_datetime += datetime.timedelta(days=1)
            
            # 如果是工作日任务，找到下一个工作日
            if task.get('workday_only', False):
                while not workday(task_datetime.date()):
                    task_datetime += datetime.timedelta(days=1)
            
            # 检查是否是最近的任务
            if next_task_time is None or task_datetime < next_task_time:
                next_task = task
                next_task_time = task_datetime
                next_task['time'] = time_str
        
        if next_task:
            # 计算剩余时间
            time_diff = next_task_time - current_time
            total_minutes = time_diff.days * 24 * 60 + time_diff.seconds // 60
            
            # 根据剩余时间确定状态
            if total_minutes <= 60:  # 1小时内
                status = 'imminent'
                status_text = '即将执行'
            elif next_task_time.date() == current_time.date():  # 今天
                status = 'today'
                status_text = '今日任务'
            elif next_task_time.date() == current_time.date() + datetime.timedelta(days=1):  # 明天
                status = 'tomorrow'
                status_text = '明日任务'
            else:  # 更远的将来
                status = 'future'
                status_text = '未来任务'
            
            # 格式化剩余时间
            if time_diff.days > 0:
                time_remaining = f"还有{time_diff.days}天{time_diff.seconds // 3600}小时{(time_diff.seconds % 3600) // 60}分钟"
            elif time_diff.seconds >= 3600:
                time_remaining = f"还有{time_diff.seconds // 3600}小时{(time_diff.seconds % 3600) // 60}分钟"
            else:
                time_remaining = f"还有{time_diff.seconds // 60}分钟"
            
            # 格式化显示日期和时间
            weekday_names = ['一', '二', '三', '四', '五', '六', '日']
            weekday = weekday_names[next_task_time.weekday()]
            display_date = next_task_time.strftime("%m月%d日")
            display_time = f"{display_date}（星期{weekday}）{next_task['time']}"
            
            return {
                'time': display_time,
                'music_file': next_task['music_file'],
                'workday_only': next_task.get('workday_only', False),
                'next_run': next_task_time.strftime('%Y-%m-%d %H:%M:%S'),
                'time_remaining': time_remaining,
                'status': status,
                'status_text': status_text
            }
        return None
    except Exception as e:
        logger.error(f"获取下一个任务失败: {str(e)}")
        return None

@app.route('/api/next-task', methods=['GET'])
@login_required
def next_task():
    """获取下一个任务的API"""
    try:
        task = get_next_task()
        if task:
            return jsonify(task)
        return jsonify({'error': '没有找到下一个任务', 'message': '请检查任务列表是否为空'}), 404
    except Exception as e:
        logger.error(f"获取下一个任务时出错: {str(e)}")
        return jsonify({'error': '获取任务信息失败', 'message': str(e)}), 500

def get_current_work_status():
    """获取当前的工作状态信息"""
    try:
        current_date = datetime.datetime.now()
        week_num = current_date.isocalendar()[1]  # 获取当前日期为今年的周数
        is_odd_week = week_num % 2 == 1
        
        # 加载周设置
        week_schedule = get_week_schedule()
        odd_week_rest = week_schedule.get('odd_week_rest', False)  # 奇数周双休
        even_week_rest = week_schedule.get('even_week_rest', False)  # 偶数周双休
        saturday_work = week_schedule.get('saturday_work', False)  # 单休周六上班
        
        # 确定本周是否单休
        is_single_rest = False
        if is_odd_week and not odd_week_rest:
            is_single_rest = True
        elif not is_odd_week and not even_week_rest:
            is_single_rest = True
            
        # 获取当前是否是工作日
        is_workday_today = workday(current_date.date())
        
        # 获取本周六是否上班
        saturday = current_date + datetime.timedelta(days=(5 - current_date.weekday()))
        is_saturday_work = workday(saturday.date()) if is_single_rest and saturday_work else False
        
        # 获取星期几的中文名称
        weekday_names = ['一', '二', '三', '四', '五', '六', '日']
        weekday = weekday_names[current_date.weekday()]
        
        return {
            'date': current_date.strftime('%Y年%m月%d日'),
            'weekday': f'星期{weekday}',
            'is_workday': is_workday_today,
            'week_num': week_num,
            'is_odd_week': is_odd_week,
            'is_single_rest': is_single_rest,
            'is_saturday_work': is_saturday_work
        }
    except Exception as e:
        logger.error(f"获取工作状态失败: {str(e)}")
        return None

@app.route('/api/work-status', methods=['GET'])
@login_required
def work_status():
    """获取当前工作状态的API"""
    status = get_current_work_status()
    if status:
        return jsonify(status)
    return jsonify({'error': '获取工作状态失败'}), 500

def start_background_threads():
    """启动后台线程"""
    try:
        logger.info("正在启动后台线程...")
        check_and_restart_schedule_thread()
        
        # 启动日历更新线程
        calendar_thread = threading.Thread(target=check_calendar_update, daemon=True)
        calendar_thread.start()
        logger.info("后台线程启动完成")
    except Exception as e:
        logger.error(f"启动后台线程失败: {str(e)}")

def check_and_restart_schedule_thread():
    """检查定时任务线程状态，如果不在运行则重新启动"""
    global schedule_thread
    try:
        # 如果线程存在且正在运行，先停止它
        if schedule_thread and schedule_thread.is_alive():
            logger.info("正在停止现有定时任务线程...")
            # 设置标志以通知线程退出
            schedule_thread.stop_flag = True
            # 等待线程完成当前循环
            schedule_thread.join(timeout=2)
            schedule_thread = None
        
        # 创建并启动新线程
        logger.info("正在创建新的定时任务线程...")
        schedule_thread = threading.Thread(target=check_schedule, daemon=True)
        schedule_thread.stop_flag = False
        schedule_thread.start()
        logger.info("定时任务线程已重新启动")
    except Exception as e:
        logger.error(f"检查或重启定时任务线程时出错: {str(e)}")

def check_schedule():
    """检查并执行定时任务"""
    # 获取当前线程对象
    current_thread = threading.current_thread()
    
    with app.app_context():
        logger.info("定时任务线程已启动")
        last_check_time = None
        
        while not getattr(current_thread, "stop_flag", False):
            try:
                now = datetime.datetime.now()
                current_time = now.strftime('%H:%M')
                
                # 避免在同一分钟内重复执行
                if current_time != last_check_time:
                    last_check_time = current_time
                    schedule = load_schedule()  # 重新加载时间表
                    
                    if current_time in schedule:
                        task = schedule[current_time]
                        if not task.get('workday_only', False) or workday(now):
                            logger.info(f"执行定时任务: {current_time} - {task['music_file']}")
                            play_music(os.path.join(MUSIC_DIR, task['music_file']))
                        else:
                            logger.info(f"跳过非工作日任务: {current_time} - {task['music_file']}")
                
                # 等待到下一秒的开始
                next_second = (now + datetime.timedelta(seconds=1)).replace(microsecond=0)
                sleep_time = (next_second - now).total_seconds()
                time.sleep(max(0, sleep_time))
                
            except Exception as e:
                logger.error(f"定时任务错误: {str(e)}")
                time.sleep(1)  # 出错时等待1秒后继续
            
            # 检查是否需要退出
            if getattr(current_thread, "stop_flag", False):
                break
        
        logger.info("定时任务线程已退出")

def load_volume():
    """从配置文件加载音量设置"""
    global current_volume
    try:
        config = load_config()
        current_volume = config.get('volume', 80)
        # 同步系统音量
        try:
            os.system(f'amixer set Master {current_volume}%')
        except Exception as e:
            logger.error(f"设置系统音量失败: {str(e)}")
    except Exception as e:
        logger.error(f"加载音量设置失败: {str(e)}")
        current_volume = 80
    return current_volume

def save_volume(volume):
    """保存音量设置到配置文件"""
    try:
        config = load_config()
        config['volume'] = volume
        if save_config(config):
            logger.info(f"音量设置已保存: {volume}%")
            return True
        return False
    except Exception as e:
        logger.error(f"保存音量设置失败: {str(e)}")
        return False

def set_volume(volume):
    """设置音量（0-100）"""
    global current_volume
    current_volume = max(0, min(100, volume))
    
    # 设置系统音量
    try:
        os.system(f'amixer set Master {current_volume}%')
    except Exception as e:
        logger.error(f"设置系统音量失败: {str(e)}")
    
    # 设置pygame音量
    if pygame.mixer.get_init():
        pygame.mixer.music.set_volume(current_volume / 100.0)
    
    # 保存音量设置
    save_volume(current_volume)
    
    logger.info(f"音量已设置为: {current_volume}%")
    return True

def get_volume():
    """获取当前音量（0-100）"""
    global current_volume
    return current_volume

@app.route('/get_volume', methods=['GET'])
def get_volume_api():
    """获取当前音量的API端点"""
    try:
        volume = get_volume()
        return jsonify({'status': 'success', 'volume': volume})
    except Exception as e:
        logger.error(f"获取音量失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/set_volume', methods=['POST'])
def set_volume_api():
    """设置音量的API端点"""
    try:
        data = request.get_json()
        volume = data.get('volume')
        if volume is None:
            return jsonify({'status': 'error', 'message': '缺少volume参数'}), 400
        
        if set_volume(volume):
            return jsonify({'status': 'success', 'volume': get_volume()})
        else:
            return jsonify({'status': 'error', 'message': '设置音量失败'}), 500
    except Exception as e:
        logger.error(f"设置音量失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def play_music(music_file):
    """播放音乐"""
    try:
        # 先停止当前播放
        stop_music()
        
        # 检查文件是否存在
        if not os.path.exists(music_file):
            logger.error(f"音乐文件不存在: {music_file}")
            return False
            
        # 确保音量已设置
        global current_volume
        if current_volume is None:
            load_volume()
            
        # 初始化之前先退出pygame
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        
        # 设置环境变量
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
        os.environ['AUDIODEV'] = 'plughw:0,0'
        
        # 使用测试成功的音频配置
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            logger.info("音频初始化成功")
            logger.info(f"音频配置: {pygame.mixer.get_init()}")
        except Exception as e:
            logger.error(f"音频初始化失败: {str(e)}")
            return False
            
        # 设置音量
        if current_volume is not None:
            try:
                pygame.mixer.music.set_volume(current_volume / 100.0)
                logger.info(f"音量设置为: {current_volume}%")
            except Exception as e:
                logger.error(f"设置音量失败: {str(e)}")
            
        # 加载并播放音乐
        logger.info(f"开始播放音乐: {music_file}")
        try:
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.play()
        except pygame.error as e:
            logger.error(f"加载或播放音乐失败: {str(e)}")
            return False
        
        # 等待一小段时间确保播放开始
        time.sleep(0.5)
        
        if pygame.mixer.music.get_busy():
            logger.info("音乐开始播放")
            return True
        else:
            logger.error("播放失败：pygame未能开始播放")
            return False
            
    except Exception as e:
        logger.error(f"播放音乐时发生错误: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False

def stop_music():
    """停止播放"""
    try:
        # 停止pygame音乐播放
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        logger.info("音乐播放已停止")
        return True
    except Exception as e:
        logger.error(f"停止播放时发生错误: {str(e)}")
        return False

def workday(date):
    """判断今天是否为工作日"""
    weekday = date.isoweekday()  # 今天是星期几
    week_of_year = date.isocalendar()[1]
    print('这周是第', week_of_year, "周")
    
    week_schedule = get_week_schedule()
    is_odd_week = week_of_year % 2 == 1
    
    if chinese_calendar.is_workday(date):
        print("今天是", date, "为工作日", single_or_weekend()[0])
        return True
    elif week_schedule["saturday_work"] and not chinese_calendar.is_in_lieu(date) and weekday == 6:
        if (is_odd_week and not week_schedule["odd_week_rest"]) or \
           (not is_odd_week and not week_schedule["even_week_rest"]):
            if date not in chinese_calendar.holidays.keys():
                print("这周单休，今天是周六，要上班哦")
                return True
    
    print("今天是", date, single_or_weekend()[0], "今天放假哦！")
    return False

def single_or_weekend():
    """判断今天是单休还是双休"""
    weeks = int(datetime.datetime.now().strftime("%W"))  # 获取当前日期为今年的周数
    week_schedule = get_week_schedule()
    
    if weeks % 2:  # 奇数周
        rs = "本周为双休" if week_schedule["odd_week_rest"] else "本周为单休", \
             'weekend' if week_schedule["odd_week_rest"] else 'single'
    else:  # 偶数周
        rs = "本周为双休" if week_schedule["even_week_rest"] else "本周为单休", \
             'weekend' if week_schedule["even_week_rest"] else 'single'
    return rs

def generate_password(password):
    """生成密码哈希"""
    return generate_password_hash(password)

def verify_password(hash, password):
    """验证密码"""
    return check_password_hash(hash, password)

def save_users(users):
    """保存用户信息"""
    try:
        users_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        app.logger.error(f"保存用户信息失败: {str(e)}")
        return False

@app.route('/api/holiday-info', methods=['GET'])
def get_holiday_info():
    """获取当前日期的节假日信息"""
    today = datetime.datetime.now().date()
    
    try:
        is_holiday = chinese_calendar.is_holiday(today)
        is_in_lieu = chinese_calendar.is_in_lieu(today)
        is_workday = chinese_calendar.is_workday(today)
        
        return jsonify({
            'is_holiday': is_holiday,
            'is_in_lieu': is_in_lieu,
            'is_workday': is_workday
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        # 设置系统默认编码为UTF-8
        if sys.platform.startswith('linux'):
            import locale
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        
        # 加载音量设置
        load_volume()
        
        # 启动后台线程
        start_background_threads()

        # 启动Flask应用
        app.run(host='0.0.0.0', port=80, threaded=True)
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        sys.exit(1)
