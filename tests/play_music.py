import datetime
from chinese_calendar import is_workday, is_in_lieu, holidays, get_holidays, Holiday, get_holiday_detail
import time
import schedule
from playsound import playsound
import sys
import os


def clear_all_job():
    schedule.clear()
    print('如果列表为空，则表示所有任务清除成功', schedule.get_jobs())


def single_or_weekend():
    weeks = int(datetime.datetime.now().strftime("%W"))  # 获取当前日期为今年的周数, 结果为整型
    # print(weeks)
    if weeks % 2:
        rs = "本周为双休", 'weekend'
    else:
        rs = "本周为单休", 'single'
    return rs


def workday(date):
    weekday = datetime.datetime.now().isoweekday()  # 今天是星期几 周一为“1” 周六为“6”；周日为“7”, 结果为整型
    # print(weekday)
    week_of_year = datetime.datetime.now().isocalendar()[1]  # datetime.IsoCalendarDate(year=2022, week=32, weekday=3)
    print('这周是第', week_of_year, "周")
    start_date_of_week = datetime.datetime.strptime(get_current_week()['start_date'], '%Y-%m-%d')
    end_date_of_week = datetime.datetime.strptime(get_current_week()['end_date'], '%Y-%m-%d')
    get_holidays_of_this_week = get_holidays(start_date_of_week, end_date_of_week, include_weekends=True)
    holiday_detail = get_holiday_detail(get_holidays_of_this_week[0])[1]
    # print(holiday_detail)
    if holiday_detail:
        for holiday in get_holidays_of_this_week:
            print('本周的节日有：', holiday, Holiday(holiday_detail).chinese)
    if is_workday(date):
        print("今天是", date, "为工作日", single_or_weekend()[0])
        return True
    elif not is_in_lieu(
            date) and weekday == 6 and not week_of_year % 2 and date not in holidays.keys():  # 判断大小周的周六是否上班（2022年单周双休，双周单休）
        print("这周单休，今天是周六，要上班哦")
        return True
    else:
        print("今天是", date, single_or_weekend()[0], "今天放假哦！")
        return False


def get_up(job_name_qch):
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + " 任务名称：" + job_name_qch)
    playsound("../qch.wav")


def broadcast_gymnastics(job_name_gbc):
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + " 任务名称：" + job_name_gbc)
    playsound("../gbc.wav")


def quit_process(self):
    print('程序结束')
    try:
        sys.exit(0)
    except:
        print('except: 程序结束!!!')
        os.system("clear")
        sys.exit()


def get_current_week():
    '''
    当周
    today_of_current_week:当前日期
    today_of_current_week.weekday() 今天为本周的第几天（从0开始计算）
    datetime.timedelta:计算2个日期的时间差
    日期的加减计算要用时间差类型（datetime.timedelta）
    '''
    today_of_current_week = datetime.date.today()
    start_date = today_of_current_week - datetime.timedelta(days=today_of_current_week.weekday())
    end_date = today_of_current_week + datetime.timedelta(days=(6 - today_of_current_week.weekday()))
    return {"start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d")}


def set_schedule():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    today_is = datetime.date(*map(int, today.split('-')))
    # print('today_is:', today_is)
    wd = datetime.datetime.now().isoweekday()
    we = {1: "星期一",
          2: "星期二",
          3: "星期三",
          4: "星期四",
          5: "星期五",
          6: "星期六",
          7: "星期天", }
    print('今天是：', we.get(wd))
    if workday(today_is):
        today = datetime.datetime.now().strftime('%Y-%m-%d')  # 获取当天日期并转换为字符
        # print(today)
        date = datetime.date(*map(int, today.split('-')))  # 用split()函数将字符串用'-'进行分割，并用map()转换为整型
        # print(date)
        # 如果今天是工作日就添加播放队列
        # schedule.every().days.at('07:52').do(workday, today=date)
        schedule.every().days.at('10:00').do(broadcast_gymnastics, '上午广播操')
        schedule.every().day.at('13:29').do(get_up, '起床号')
        schedule.every().days.at('15:00').do(broadcast_gymnastics, '下午广播操')
        # schedule.every().days.at('15:06').do(quit_process, '结束本程序')
        print(schedule.get_jobs())
        schedule.every().day.at("23:59").do(clear_all_job)
        weekday = datetime.datetime.now().isoweekday() + 1
        wd = datetime.datetime.now().isoweekday()
        all_job = schedule.get_jobs()
        for job in all_job:
            print(job.tag)
        while wd != weekday:
            schedule.run_pending()
            wd = datetime.datetime.now().isoweekday()
            # print("今天是星期：{}".format(wd))
            time.sleep(3)
    else:
        # 如果今天为假日，程序休眠24小时
        print("现在是{}程序进入休眠状态，24小时后再见".format(datetime.datetime.now()))
        time.sleep(60 * 60 * 24)


while True:
    set_schedule()
    print("程序重启")
    # time.sleep(60 * 60 * 6)
