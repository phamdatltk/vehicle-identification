import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import grpc
import torch
import numpy as np
from concurrent import futures
from PIL import Image
import yaml
import logging

from wpodnet.backend import Predictor
from wpodnet.model import WPODNet

import protos.platecrop_pb2_grpc as platecrop_pb2_grpc
import protos.platecrop_pb2 as platecrop_pb2
import protos.types_pb2 as types_pb2

from utills import bts_to_img, image_to_bts
from logger import logger_handler

exec_name = os.path.basename(__file__)
logging.basicConfig(handlers=[logger_handler()])
log = logging.getLogger(exec_name)
log.setLevel(logging.DEBUG)

CONFIG_FILE = "./config/PlateCropService.yml"
log.info(f"Reading config file: {CONFIG_FILE}")
config = None
with open(CONFIG_FILE, "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
log.setLevel(logging.DEBUG if config["debug"] else logging.INFO)
log.debug(f"Config: {config}")
    
INSECURE_PORTS = config["insecure_ports"]

class PlateCropServicer(platecrop_pb2_grpc.PlateCropServicer):
    def __init__(self):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = WPODNet()
        model.to(device)
        checkpoint = torch.load('./wpodnet.pth')
        model.load_state_dict(checkpoint)
        self.wpod_model = Predictor(model)
    
    def Crop(self, request, context):
        img_bts = request.data
        img = bts_to_img(img_bts)
        prediction = self.wpod_model.predict(Image.fromarray(np.uint8(img)).convert('RGB'))
        if prediction.confidence > 0.9:
            img = np.array(prediction.warp())
        img_bts = image_to_bts(img)
        response = types_pb2.Image(
            data=img_bts
        )
        return response

def serve(silent:bool):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=config["n_threads"]))
    platecrop_pb2_grpc.add_PlateCropServicer_to_server(PlateCropServicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    log.info(f"[PlateCrop] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)