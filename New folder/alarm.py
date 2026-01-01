
import time
import datetime
import os

# Try to import pygame; if unavailable, we'll fall back to platform beep (winsound on Windows)
try:
    import pygame
    HAS_PYGAME = True
except Exception:
    pygame = None
    HAS_PYGAME = False

try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    winsound = None
    HAS_WINSOUND = False

def set_alarm(alarm_time):
    print(f"Alarm set for {alarm_time}")
    sound_file = "videoplayback.m4a"

    is_running = True

    while is_running:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"Current time: {current_time}", end="\r")

        if current_time == alarm_time:
            print("\nAlarm time reached!")

            # If pygame is available and the sound file exists, use it.
            if HAS_PYGAME and os.path.exists(sound_file):
                try:
                    pygame.mixer.init()
                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play(-1)  # Play the sound in a loop
                    print("Alarm ringing! Press Ctrl+C to stop.")
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pygame.mixer.music.stop()
                    is_running = False
                    print("\nAlarm stopped.")
                except Exception as e:
                    print(f"Error playing sound with pygame: {e}")
                    is_running = False
            else:
                # Fallback: use winsound.Beep on Windows for a short sequence
                if HAS_WINSOUND:
                    try:
                        print("Playing fallback beep (winsound).")
                        for _ in range(5):
                            winsound.Beep(1000, 700)  # frequency, duration(ms)
                            time.sleep(0.1)
                        is_running = False
                        print("Alarm stopped (fallback).")
                    except Exception as e:
                        print(f"Fallback beep failed: {e}")
                        is_running = False
                else:
                    print("No audio backend available (pygame not installed and winsound unavailable).")
                    is_running = False

# Get alarm time from user
if __name__ == "__main__":
    try:
        alarm_time = input("Enter alarm time in HH:MM:SS format (e.g., 07:30:00): ")
        set_alarm(alarm_time)
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
