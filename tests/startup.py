import time
import schedule
import os


def restart_up():
    os.system('python3 play_music.py')


schedule.every().day.at('09:30').do(restart_up)
restart_up()
while True:
    schedule.run_pending()
    time.sleep(1)
