from flask import Flask, render_template, Response, request, jsonify
from imutils.video import VideoStream
import threading
import datetime
import time
import cv2
import os
from Notifier import notify
from Blink_detection import blink_detection

app = Flask(__name__)

outputFrame = None
lock = threading.Lock()

# Initialize global variables
timediff = datetime.datetime.now()
screen_time = 0
last_notified = datetime.datetime.now()
last_20_20_20 = datetime.datetime.now()

# Notification and reminder settings
blink_reminder_enabled = True
rule_20_20_20_enabled = True

# Eye aspect ratio to indicate blink
EYE_AR_THRESH = 0.22
EYE_AR_CONSEC_FRAMES_MIN = 2
EYE_AR_CONSEC_FRAMES_MAX = 5
BLINK_TIME_THRESH = 8

vs = VideoStream(src=0).start()
time.sleep(1.0)

@app.route("/")
def index():
    return render_template("index.html", blink_reminder=blink_reminder_enabled, rule_20_20_20=rule_20_20_20_enabled)

@app.route("/toggle_blink_reminder", methods=["POST"])
def toggle_blink_reminder():
    global blink_reminder_enabled
    blink_reminder_enabled = request.json.get("blink_reminder", True)
    return jsonify({"success": True})

@app.route("/toggle_20_20_20_rule", methods=["POST"])
def toggle_20_20_20_rule():
    global rule_20_20_20_enabled
    rule_20_20_20_enabled = request.json.get("rule_20_20_20", True)
    return jsonify({"success": True})

def detect_blinks():
    global vs, outputFrame, lock, screen_time, last_notified, last_20_20_20, blink_reminder_enabled, rule_20_20_20_enabled

    counter = 0
    totalBlinks = 0
    last_blink_time = datetime.datetime.now()
    eye_open_start = None

    while True:
        frame = vs.read()
        frame = cv2.resize(frame, (700, 500))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        EAR = blink_detection.calculate_ear(frame, gray)

        if EAR is not None:
            if EAR < EYE_AR_THRESH:
                counter += 1
                eye_open_start = None
            else:
                if EYE_AR_CONSEC_FRAMES_MIN <= counter <= EYE_AR_CONSEC_FRAMES_MAX:
                    totalBlinks += 1
                    last_blink_time = datetime.datetime.now()

                counter = 0

                if eye_open_start is None:
                    eye_open_start = datetime.datetime.now()
                else:
                    screen_time += (datetime.datetime.now() - eye_open_start).total_seconds()
                    eye_open_start = datetime.datetime.now()

            cv2.putText(frame, "Blinks: {}".format(totalBlinks), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "EAR: {:.2f}".format(EAR), (300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "Screen Time: {:.2f}s".format(screen_time), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            if blink_reminder_enabled and (datetime.datetime.now() - last_blink_time).total_seconds() > BLINK_TIME_THRESH:
                if eye_open_start is not None and (datetime.datetime.now() - last_notified).total_seconds() > BLINK_TIME_THRESH:
                    notify("Reminder to Blink!", "STRAIN ALERT")
                    last_notified = datetime.datetime.now()

            if rule_20_20_20_enabled and screen_time > 20:
                if (datetime.datetime.now() - last_20_20_20).total_seconds() > 20:
                    notify("20-20-20 Rule", "Look at something 20 feet away for 20 seconds.")
                    last_20_20_20 = datetime.datetime.now()

        with lock:
            outputFrame = frame.copy()

def generate():
    global outputFrame, lock

    while True:
        with lock:
            if outputFrame is None:
                continue

            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            if not flag:
                continue

        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    t = threading.Thread(target=detect_blinks)
    t.daemon = True
    t.start()
    app.run(debug=True, threaded=True, use_reloader=False)

vs.stop()
cv2.destroyAllWindows()
