import os

import vidgear.gears
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
import grpc
import random
import datetime
import time
import numpy as np
import multiprocessing as mp
import yaml

from flask import Flask, Response, request, render_template, render_template_string
from urllib.parse import unquote
from waitress import serve
import logging

import protos.imgresize_pb2_grpc as imgresize_pb2_grpc
import protos.imgresize_pb2 as imgresize_pb2
import protos.yolov8_pb2_grpc as yolov8_pb2_grpc
import protos.yolov8_pb2 as yolov8_pb2
import protos.platecrop_pb2_grpc as platecrop_pb2_grpc
import protos.platecrop_pb2 as platecrop_pb2
import protos.ocr_pb2_grpc as ocr_pb2_grpc
import protos.ocr_pb2 as ocr_pb2
import protos.imgcolor_pb2_grpc as imgcolor_pb2_grpc
import protos.imgcolor_pb2 as imgcolor_pb2
import protos.types_pb2 as types_pb2

import protos.identify_pb2_grpc as identify_pb2_grpc
import protos.identify_pb2 as identify_pb2

from utills import drawText, bts_to_img, image_to_bts, is_number
from logger import GetLogger, logger_handler

exec_name = os.path.basename(__file__)
logging.basicConfig(handlers=[logger_handler()])
log = logging.getLogger(exec_name)
log.setLevel(logging.DEBUG)

CONFIG_FILE = "./config/WebServer.yml"
log.info(f"Reading config file: {CONFIG_FILE}")
config = None
with open(CONFIG_FILE, "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
log.setLevel(logging.DEBUG if config["debug"] else logging.INFO)
log.debug(f"Config: {config}")

IDENTIFY_CHANNEL = config["identify_channel"]

identify_stub = identify_pb2_grpc.IdentifyStub(
    grpc.insecure_channel(IDENTIFY_CHANNEL)
)

input_stream_options = {
    "STREAM_RESOLUTION": "1080p",
    "THREAD_TIMEOUT": 30,
    "CAP_PROP_FPS": 15,
    'THREADED_QUEUE_MODE': True
}

def IdentifyImage(frame:np.ndarray) -> np.ndarray:
    dtr = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")    
    st = time.perf_counter()
    frame_str = image_to_bts(frame)
    identify_response = identify_stub.Identify(types_pb2.Image(data=frame_str))
    idens = identify_response.vehicles
    for iden in idens:
        color_code = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
        cv2.rectangle(
            frame, 
            (int(iden.x0), int(iden.y0)), (int(iden.x1), int(iden.y1)), 
            color=color_code, 
            thickness=2
        )
        frame = drawText(
            frame, iden.id,
            text_position=(int(iden.x0), int(iden.y0)), 
            text_color=color_code
        )
    st = time.perf_counter() - st    
    st = round(st*1000)
    frame = drawText(
        frame, f"{dtr} @ {st}ms",
        text_position=(0,0), 
        text_color=(255,0,0)
    )
    return frame

def feed(src, quality, noskip):
    input_stream_options["STREAM_RESOLUTION"] = quality
    input_stream_options["THREADED_QUEUE_MODE"] = bool(int(noskip))
    start_time = time.time()
    capture = vidgear.gears.CamGear(src, stream_mode=True, logging=config["debug"], **input_stream_options).start()
    while True:
        diff_time = time.time() - start_time
        if diff_time > 60:
            break
        frame = capture.read()
        if frame is None:
            break
        frame = IdentifyImage(frame)
        start_time = time.time()
        yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(cv2.imencode(".jpg", frame)[1]) + b'\r\n'
    capture.stop()
    return

app = Flask(__name__)

homepage_contents = None
with open("./README.md", mode="rt", encoding='utf-8') as f:
    homepage_contents = ''.join(f.readlines())

with open("./templates/index.html", mode="rt", encoding='utf-8') as f:
    homepage_template = ''.join(f.readlines())
homepage = homepage_template.replace("{"+"{"+"readmecontent"+"}"+"}", homepage_contents)

@app.route("/", methods=["GET"])
def hello_world():
    return Response(
        homepage, status=200
    )
    
@app.route("/api/identify", methods=["POST"])
def identify():
    start_time_total = time.perf_counter()
    data = request.data
    img = np.asarray(bytearray(data))
    img = cv2.imdecode(img, cv2.IMREAD_COLOR)
    img = IdentifyImage(img)
    _, img = cv2.imencode('.png', img)
    end_time_total = time.perf_counter()
    elapsed_time_total = round((end_time_total - start_time_total) * 1000, 2)
    log.info(f"TOTAL TIME WEB SERVER: {elapsed_time_total} ms")
    return Response(img.tobytes(), status=200, content_type='image/png')
    
@app.route("/stream")
def stream():
    url = request.args.get("url", default="https://www.youtube.com/watch?v=dQw4w9WgXcQ", type=str)
    quality = request.args.get("quality", default="480p")
    noskip = request.args.get("noskip", default="1")
    if is_number(url):
        url = int(url)
    else:
        url = unquote(url)
    return Response(
        feed(url, quality, noskip),
        mimetype = "multipart/x-mixed-replace; boundary=frame"
    )

if __name__=="__main__":
    log.info(f"[WebServer] {config['host']}:{config['port']} n_threads={config['n_threads']}")
    if config["dev"]:
        log.info("Runing in DEV mode !!!")
        app.run(
            host=config["host"],
            port=config["port"],
            debug=config["debug"],
            threaded=config["threaded"],
            use_reloader=config["use_reloader"]
        )
    else:
        serve(
            app,
            host=config["host"],
            port=config["port"],
            threads=config["n_threads"]
        )