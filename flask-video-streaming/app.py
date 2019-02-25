#!/usr/bin/env python
import os
from importlib import import_module

from flask import Flask, render_template, Response

# import camera driver
if os.environ.get('CAMERA'):
    Camera = import_module('camera_' + os.environ['CAMERA']).Camera
else:
    from camera.camera_opencv import Camera

from web_socket import  websocket_client
# Raspberry Pi camera module (requires picamera package)
# from camera_pi import Camera

app = Flask(__name__)
web_socket_server = None

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('monitor.html')


def gen(camera):
    """Video streaming generator function."""

    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera(web_socket_server)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/image_feed')
# def image_feed():
#     """Video streaming route. Put this in the src attribute of an img tag."""
#     from camera import camera_image
#     return Response(gen(camera_image.Camera()),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    # 启动识别监听线程
    web_socket_server = websocket_client.websocket_server(9000)
    web_socket_server.start()

    app.run(host='0.0.0.0', threaded=True)


