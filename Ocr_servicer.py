import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import grpc
import easyocr
from concurrent import futures
import yaml

import protos.ocr_pb2_grpc as ocr_pb2_grpc
import protos.ocr_pb2 as ocr_pb2
import protos.types_pb2 as types_pb2

from utills import bts_to_img, image_to_bts

config = None
with open("./config/OcrService.yml", "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
    
INSECURE_PORTS = config["insecure_ports"]

class OcrServicer(ocr_pb2_grpc.OcrServicer):
    def __init__(self):
        self.ocr_model = easyocr.Reader(["en"], verbose=False, model_storage_directory=".")
    
    def ReadText(self, request, context):
        img_bts = request.data
        img = bts_to_img(img_bts)
        
        ocr_result = self.ocr_model.readtext(img, paragraph=True, detail=0)
        
        response = types_pb2.OcrResult(
            text=ocr_result
        )
        return response

def serve(silent:bool):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ocr_pb2_grpc.add_OcrServicer_to_server(OcrServicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    print(f"[Ocr] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)