import os
import sys
import time
import pygame
import array

def test_audio():
    print("开始音频测试...")
    
    # 设置环境变量
    os.environ['SDL_AUDIODRIVER'] = 'alsa'
    os.environ['AUDIODEV'] = 'plughw:0,0'
    
    # 测试不同的配置
    configs = [
        {'frequency': 44100, 'size': -16, 'channels': 2, 'buffer': 512},
        {'frequency': 48000, 'size': -16, 'channels': 2, 'buffer': 1024},
        {'frequency': 44100, 'size': -16, 'channels': 1, 'buffer': 2048},
        {}  # 默认配置
    ]
    
    for i, config in enumerate(configs):
        print(f"\n测试配置 {i+1}:")
        print(config if config else "默认配置")
        
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            
            if config:
                pygame.mixer.init(**config)
            else:
                pygame.mixer.init()
            
            print("初始化成功!")
            print(f"实际音频配置: {pygame.mixer.get_init()}")
            
            # 生成简单的测试音频
            duration = 1.0  # 1秒
            sample_rate = pygame.mixer.get_init()[0]
            num_samples = int(duration * sample_rate)
            
            # 创建一个简单的方波
            buffer = array.array('h', [0] * num_samples)  # 16-bit 音频
            amplitude = 32767 // 4  # 四分之一最大音量
            
            for i in range(num_samples):
                if (i // 50) % 2:  # 每50个样本切换一次
                    buffer[i] = amplitude
                else:
                    buffer[i] = -amplitude
            
            # 创建声音对象并播放
            try:
                sound = pygame.mixer.Sound(buffer=buffer)
                print("正在播放测试音频...")
                sound.play()
                time.sleep(1)
                print("测试音频播放完成")
                return True
            except Exception as e:
                print(f"播放测试音频失败: {e}")
            
        except Exception as e:
            print(f"配置失败: {e}")
            continue
            
    print("\n所有配置都失败了")
    return False

if __name__ == "__main__":
    if test_audio():
        print("\n音频测试成功!")
    else:
        print("\n音频测试失败!")
        sys.exit(1)
