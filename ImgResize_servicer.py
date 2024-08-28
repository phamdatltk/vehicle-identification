import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import grpc
import cv2
from concurrent import futures
import yaml

import protos.imgresize_pb2_grpc as imgresize_pb2_grpc
import protos.imgresize_pb2 as imgresize_pb2
import protos.types_pb2 as types_pb2

from utills import bts_to_img, image_to_bts

config = None
with open("./config/ImgResizeService.yml", "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
    
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
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    imgresize_pb2_grpc.add_ImgResizeServicer_to_server(ImgResizeServicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    print(f"[ImgResize] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)