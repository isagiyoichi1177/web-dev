def set_alarm(alarm_time):
    print(f"Alarm set for {alarm_time}")
    sound_file = "videoplayback.m4a" 
    is_running = True
    
    while is_running:
        currrent_time = datetime.datetime.now().strftime("%H:%M:%S:")
        print(currrent_time)
        # Replace with your alarm sound file path
        if current_time == alarm_time:
            pygame.mixer.init()
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play(-1)  # Play the sound in a loop
            print("Alarm ringing! Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pygame.mixer.music.stop()
                is_running = False
                print("Alarm stopped.")
