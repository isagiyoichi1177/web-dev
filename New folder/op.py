
import time
import pygame
import datetime

def set_alarm
(time_str):
    pygame.mixer.init()
    alarm_time = datetime.datetime.strptime(time_str, "%H:%M").time()
    print(f"Alarm set for {alarm_time.strftime('%H:%M')}")

    while True:
        now = datetime.datetime.now().time()
        if now.hour == alarm_time.hour and now.minute == alarm_time.minute:
            print("Alarm ringing!")
            pygame.mixer.music.load("alarm_sound.mp3")
            pygame.mixer.music.play(-1)
            break
        time.sleep(30)  # Check every 30 seconds