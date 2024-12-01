'''import datetime
# from chinese_calendar import is_holiday
from chinese_calendar import is_workday
from chinese_calendar import is_in_lieu
import time
import pyaudio
import wave
import schedule'''
from playsound import playsound
# import sys

'''today = datetime.datetime.now().strftime('%Y-%m-%d')  # 获取当天日期并转换为字符
# print(today)
date = datetime.date(*map(int, today.split('-')))  # 用split()函数将字符串用'-'进行分割，并用map()转换为整型
# print(date)
weeks = int(datetime.datetime.now().strftime("%W"))  # 获取当前日期为今年的周数, 结果为整型
# print(weeks)
weekday = datetime.datetime.now().isoweekday()  # 今天是星期几 周一为“1” 周六为“6”；周日为“7”, 结果为整型
# print(weekday)
week_of_year = datetime.datetime.now().isocalendar() [1] # datetime.IsoCalendarDate(year=2022, week=32, weekday=3)
print(week_of_year)

# print(iso_calendar)  # 结果为整型
# print(is_in_lieu(date))  # 是否为调休
# print(weekday == 6)  # 是否为周六
# print(not iso_calendar.week % 2)  # 单休还是双休
def workday(date):
    if is_workday(date):
        # print("今天是工作日")
        return True
    elif not is_in_lieu(date) and weekday == 6 and not week_of_year % 2:  # 判断大小周的周六是否上班（2022年单周双休，双周单休）
        # print("这周单休，今天是周六，要上班哦")
        return True
    else:
        return False


# print(workday(date))
def play_music(path):
    wf = wave.open(path, "rb")
    wav_data = wf.readframes(wf.getnframes())
    meta = {"seek": 0}  # int变量不能传进函数内部，会有UnboundLocalError，所以给它套上一层壳

    def callback(in_data, frame_count, time_info, status):
        # 这是针对流式录制，只有二进制数据没有保存到本地的wav文件时的做法，通过文件指针偏移读取数据
        start = meta["seek"]
        meta["seek"] += frame_count * pyaudio.get_sample_size(pyaudio.paInt16) * wf.getnchannels()
        data = wav_data[start: meta["seek"]]
        # 如果有保存成wav文件，直接用文件句柄readframes就行，不用像上面那么麻烦
        #     data = wf.readframes(frame_count)
        return (data, pyaudio.paContinue)

    audio = pyaudio.PyAudio()
    stream = audio.open(format=audio.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                        stream_callback=callback)

    stream.start_stream()
    # 对callback更进一步的理解见本文下一段的“根据文档原话学pyaudio”以及"根据实验结果推测pyaudio的内部实现"
    # 划重点：start_stream()之后stream会开始调用callback函数并把得到的data进行stream.write()，
    # 直到状态码变为paComplete就停止读取（一般是到达音频文件末尾）。由于回调函数是通过另开线程调用的，
    # 它也需要像平常多线程代码一样有类似join的操作，否则主线程stop_stream()就没了。因此这里的while循环必不可少，
    # 当stream仍处于活跃状态（应该就是音频文件还没读完）时，让主线程休眠，也就是让主线程等子线程执行完。
    # 而我们又可以在while循环里添加一些条件判断，在整个音频播放完成之前提前跳出循环，结束播放，这样就实现了前面所说的实时问答，打断说话的效果
    # stream初始化后到stop_stream()之前，is_active()都是True，stop_stream()之后变成False，start_stream()之后又变成True，它表示的是这个流是否开放读写，实际上也对应音频数据是否读完，因为数据一读完stream就会被stop
    while stream.is_active():
        time.sleep(0.1)
    stream.stop_stream()
    stream.close()
    wf.close()
    audio.terminate()

'''
# def get_up():
# playsound("../qch.wav")


# def broadcast_gymnastics():
playsound("../gbc.wav")


'''if workday(date):
    # 如果今天是工作日就添加播放队列
    # schedule.every(10).days.do(broadcast_gymnastics)
    # schedule.every(15).days.do(broadcast_gymnastics)
    # schedule.every().day.at('13:30').do(get_up)
    schedule.every().day.at('23:54').do(get_up)
    schedule.every().day.at('14:44').do(broadcast_gymnastics)

while True:
    schedule.run_pending()
    time.sleep(1)
'''