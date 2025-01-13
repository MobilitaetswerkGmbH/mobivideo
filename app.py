from flask import Flask, render_template, request, redirect, url_for, jsonify
import schedule
import time
import subprocess
from threading import Thread
import os
from datetime import datetime, timedelta
import shutil
from picamerax import PiCamera
#from libcamera import controls

app = Flask(__name__)

CORRECT_PASSWORD = 'MobiData24'
USB_MOUNT_PATH = '/media/usb_drive'
SOURCE_FOLDER = '/home/pi/Videos'
TARGET_FOLDER = USB_MOUNT_PATH + '/Videos/mobivideo17'

is_recording = False
recording_duration = None
current_start_time = None
current_stop_time = None

def get_device_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def set_device_time(new_time):
    try:
        os.system(f"sudo date -s '{new_time}'")
        os.system("sudo hwclock -w")
        return True
    except Exception as e:
        print(f"Error setting device time: {e}")
        return False

def start_recording():
    global is_recording, recording_duration
    if not is_recording:
        is_recording = True
        duration_param = [str(recording_duration)] if recording_duration else []
        subprocess.Popen(["python3", "record.py", "start"] + duration_param)

def stop_recording():
    global is_recording
    subprocess.Popen(["python3", "record.py", "stop"])
    is_recording = False

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def capture_preview():
    # Initialize PiCameraX
    with PiCamera() as picam:
        picam.resolution = (800, 600)
        picam.iso = 0
        picam.start_preview()
        time.sleep(2)
        preview_image_path = 'static/preview.jpg'
        picam.capture(preview_image_path)

scheduler_thread = Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

@app.route('/')
def index():
    global current_start_time, current_stop_time, is_recording
    preview_image = url_for('static', filename='preview.jpg') if os.path.exists('static/preview.jpg') else None
    current_schedule = {
        'start_time': current_start_time.strftime("%H:%M") if current_start_time else '',
        'stop_time': current_stop_time.strftime("%H:%M") if current_stop_time else ''
    }
    device_time = get_device_time()
    return render_template('index.html', preview_image=preview_image, current_schedule=current_schedule, is_recording=is_recording, device_time=device_time)

@app.route('/set_schedule', methods=['POST'])
def set_schedule():
    global recording_duration, current_start_time, current_stop_time
    start_time = request.form['start_time']
    stop_time = request.form['stop_time']

    schedule.clear()

    start_dt = datetime.strptime(start_time, "%H:%M")
    stop_dt = datetime.strptime(stop_time, "%H:%M")
    now = datetime.now()

    start_dt = datetime.combine(now.date(), start_dt.time())
    stop_dt = datetime.combine(now.date(), stop_dt.time())
    if stop_dt <= start_dt:
        stop_dt += timedelta(days=1)

    recording_duration = int((stop_dt - start_dt).total_seconds())
    current_start_time = start_dt
    current_stop_time = stop_dt

    schedule.every().day.at(start_time).do(start_recording)
    schedule.every().day.at(stop_time).do(stop_recording)

#    if now.time() > start_dt.time() and now.time() < stop_dt.time():
#        start_recording()

    return redirect(url_for('index'))

@app.route('/remove_schedule', methods=['POST'])
def remove_schedule():
    global current_start_time, current_stop_time
    schedule.clear()
    current_start_time = None
    current_stop_time = None
    return redirect(url_for('index'))

@app.route('/capture_preview', methods=['POST'])
def capture_preview_route():
    capture_preview()
    return redirect(url_for('index'))

@app.route('/set_start_time_to_now', methods=['POST'])
def set_start_time_to_now():
    now = datetime.now().strftime("%H:%M")
    return jsonify(time=now)

@app.route('/get_status', methods=['GET'])
def get_status():
    global is_recording
    return jsonify(is_recording=is_recording)

@app.route('/stop_recording', methods=['POST'])
def stop_recording_route():
    stop_recording()
    global is_recording
    return jsonify({'success': True, 'is_recording': is_recording})

@app.route('/disable_wifi_bluetooth', methods=['POST'])
def disable_wifi_bluetooth():
    print("Received request to disable Wi-Fi and Bluetooth")
    try:
        # Disable Wi-Fi
        os.system("/usr/bin/sudo ifconfig wlan0 down")
        # Disable Hotspot
        os.system("/usr/bin/sudo ifconfig uap0 down")
        return redirect(url_for('index'))
    except Exception as e:
        return str(e)

@app.route('/set_time', methods=['POST'])
def set_time():
    if request.method == 'POST':
        new_time = request.form.get('new_time')
        if set_device_time(new_time):
            return jsonify(success=True)
        else:
            return jsonify(success=False)

@app.route('/transfer', methods=['POST'])
def transfer():
    global current_start_time, current_stop_time, is_recording
    
    current_schedule = {
        'start_time': current_start_time.strftime("%H:%M") if current_start_time else '',
        'stop_time': current_stop_time.strftime("%H:%M") if current_stop_time else ''
    }
    device_time = get_device_time()
    preview_image = url_for('static', filename='preview.jpg') if os.path.exists('static/preview.jpg') else None
    
    password = request.form.get('password')

    if password != CORRECT_PASSWORD:
        return render_template('index.html', message="Incorrect password!", preview_image=preview_image, current_schedule=current_schedule, is_recording=is_recording, device_time=device_time)

    if not os.path.ismount(USB_MOUNT_PATH):
        return render_template('index.html', message="USB drive is not mounted!", preview_image=preview_image, current_schedule=current_schedule, is_recording=is_recording, device_time=device_time)

    if not os.path.exists(TARGET_FOLDER):
        os.makedirs(TARGET_FOLDER)

    try:
        for filename in os.listdir(SOURCE_FOLDER):
            source_file = os.path.join(SOURCE_FOLDER, filename)
            target_file = os.path.join(TARGET_FOLDER, filename)
            shutil.move(source_file, target_file)

        return render_template('index.html', message="File transfer complete!", preview_image=preview_image, current_schedule=current_schedule, is_recording=is_recording, device_time=device_time)
    except Exception as e:
        return render_template('index.html', message=f"Error during file transfer: {str(e)}", preview_image=preview_image, current_schedule=current_schedule, is_recording=is_recording, device_time=device_time)

if __name__ == '__main__':
    if os.path.exists('static/preview.jpg'):
        os.remove('static/preview.jpg')
    app.run(host='0.0.0.0', port=5000)
