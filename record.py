import time
import os
import sys
import datetime as dt
import signal
import picamerax
import socket

STOP_FLAG_FILE = "/tmp/recording_stop_flag"
OUTPUT_DIR = os.path.expanduser("/home/pi/Videos")
SEGMENT_TIME = 3600
HOSTNAME = socket.gethostname()
FRAMERATE = 15

def check_stop_flag():
    return os.path.exists(STOP_FLAG_FILE)

def set_stop_flag():
    with open(STOP_FLAG_FILE, 'w') as f:
        f.write('stop')

def clear_stop_flag():
    if os.path.exists(STOP_FLAG_FILE):
        os.remove(STOP_FLAG_FILE)

def start_recording(duration=None):
    clear_stop_flag()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with picamerax.PiCamera(
        framerate = FRAMERATE,
        resolution = (800, 600)
    ) as camera:
        camera.annotate_background = picamerax.Color("black")
        camera.exposure_mode = "nightpreview"
        camera.drc_strength = "high"
        camera.rotation = 180
        camera.awb_mode = "greyworld"
        camera.meter_mode = "average"
        camera.iso = 0

        while not check_stop_flag():
            print("Recording new Segment")
            timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            camera.start_preview()
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.start_recording(
                output = f"{OUTPUT_DIR}/{HOSTNAME}_{FRAMERATE}_{timestamp}.h264",
                format = "h264",
    #           resize = (800, 600),
                profile = "high",
                level = "4",
                bitrate = 600000,
                quality = 30
            )
            start = dt.datetime.now()
            while (dt.datetime.now() - start).seconds < SEGMENT_TIME:
                if check_stop_flag():
                    break
                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.wait_recording(0.1)
            camera.stop_recording()
            camera.stop_preview()
            if not check_stop_flag():
                print("Restarting recording...")
            else:
                camera.close()

def stop_recording():
    print("Stopping Recording")
    set_stop_flag()

def signal_handler(signum, frame):
    stop_recording()

if __name__ == "__main__":
    import sys

    signal.signal(signal.SIGTERM, signal_handler)

    if len(sys.argv) < 2:
        print("Usage: record.py start [duration] or record.py stop")
        sys.exit(1)

    action = sys.argv[1]
    if action == "start":
        duration = int(sys.argv[2]) if len(sys.argv) == 3 else None
        start_recording(duration)
    elif action == "stop":
        stop_recording()
    else:
        print("Unknown action:", action)
        sys.exit(1)
