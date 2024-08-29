import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import grpc
from ultralytics import YOLO
import yaml
from concurrent import futures
import logging

import protos.yolov8_pb2_grpc as yolov8_pb2_grpc
import protos.yolov8_pb2 as yolov8_pb2
import protos.types_pb2 as types_pb2

from utills import bts_to_img, image_to_bts
from logger import logger_handler

exec_name = os.path.basename(__file__)
logging.basicConfig(handlers=[logger_handler()])
log = logging.getLogger(exec_name)
log.setLevel(logging.DEBUG)

CONFIG_FILE = "./config/YoloService.yml"
log.info(f"Reading config file: {CONFIG_FILE}")
config = None
with open(CONFIG_FILE, "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
log.setLevel(logging.DEBUG if config["debug"] else logging.INFO)
log.debug(f"Config: {config}")

INSECURE_PORTS = config["insecure_ports"]

class Yolov8Servicer(yolov8_pb2_grpc.Yolov8Servicer):
    def __init__(self):
        self.yolo_model = YOLO(verbose=False)
    
    def Detect(self, request, context):
        img_bts = request.data
        img = bts_to_img(img_bts)
        
        detect_results = self.yolo_model.track(img, verbose=False)
        boxes = detect_results[0].boxes
        boxes_pb2 = []
        for box in boxes:
            x0, y0, x1, y1 = box.xyxyn[0].tolist()
            id = "#"
            if not (box.id is None):
                id = str(box.id[0].item())
            box_pb2 = types_pb2.Box(
                x0=x0, y0=y0, x1=x1, y1=y1, id=f"{id}_{detect_results[0].names[int(round(box.cls[0].item()))]}"
            )
            boxes_pb2.append(box_pb2)
        response = types_pb2.DetectResult(
            boxes=boxes_pb2
        )
        return response

def serve(silent:bool):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=config["n_threads"]))
    yolov8_pb2_grpc.add_Yolov8Servicer_to_server(Yolov8Servicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    log.info(f"[Yolov8] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)