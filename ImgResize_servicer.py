import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import grpc
import cv2
from concurrent import futures
import yaml
import logging

import protos.imgresize_pb2_grpc as imgresize_pb2_grpc
import protos.imgresize_pb2 as imgresize_pb2
import protos.types_pb2 as types_pb2

from utills import bts_to_img, image_to_bts
from logger import logger_handler

exec_name = os.path.basename(__file__)
logging.basicConfig(handlers=[logger_handler()])
log = logging.getLogger(exec_name)
log.setLevel(logging.DEBUG)

CONFIG_FILE = "./config/ImgResizeService.yml"
log.info(f"Reading config file: {CONFIG_FILE}")
config = None
with open(CONFIG_FILE, "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
log.setLevel(logging.DEBUG if config["debug"] else logging.INFO)
log.debug(f"Config: {config}")

INSECURE_PORTS = config["insecure_ports"]

class ImgResizeServicer(imgresize_pb2_grpc.ImgResizeServicer):
    def To480p(self, request, context):
        img_bts = request.data
        img = bts_to_img(img_bts)
        
        (h, w) = img.shape[:2]
        new_height = 480
        aspect_ratio = w/h
        new_width = int(new_height * aspect_ratio)
        img = cv2.resize(img, (new_width, new_height))
        
        img_bts = image_to_bts(img)
        response = types_pb2.Image(
            data=img_bts
        )
        return response

def serve(silent:bool):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=config["n_threads"]))
    imgresize_pb2_grpc.add_ImgResizeServicer_to_server(ImgResizeServicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    log.info(f"[ImgResize] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)