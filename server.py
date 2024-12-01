from flask import Flask, render_template, jsonify, request
import os
import pygame
import logging
from play_music import play_music, stop_music

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量存储当前音量
current_volume = 80

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play')
def play():
    try:
        music_file = os.path.join(os.path.dirname(__file__), 'music', '起床号.wav')
        if play_music(music_file):
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': '播放失败'})
    except Exception as e:
        logger.error(f"播放音乐时发生错误: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stop')
def stop():
    try:
        if stop_music():
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': '停止失败'})
    except Exception as e:
        logger.error(f"停止音乐时发生错误: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/set_volume', methods=['POST'])
def set_volume():
    try:
        data = request.get_json()
        volume = int(data.get('volume', 80))
        
        # 确保音量在有效范围内
        volume = max(0, min(100, volume))
        
        # 更新全局音量
        global current_volume
        current_volume = volume
        
        # 如果 pygame 已初始化，设置音量
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(volume / 100.0)
            
        logger.info(f"音量已设置为: {volume}%")
        return jsonify({'status': 'success', 'volume': volume})
    except Exception as e:
        logger.error(f"设置音量时发生错误: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_volume')
def get_volume():
    return jsonify({'status': 'success', 'volume': current_volume})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
