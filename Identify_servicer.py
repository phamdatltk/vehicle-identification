import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from concurrent import futures
import cv2
import math
import grpc
import yaml
import logging
import time

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

from utills import drawText, bts_to_img, image_to_bts
from logger import logger_handler

exec_name = os.path.basename(__file__)
logging.basicConfig(handlers=[logger_handler()])
log = logging.getLogger(exec_name)
log.setLevel(logging.DEBUG)

CONFIG_FILE = "./config/IdentifyService.yml"
log.info(f"Reading config file: {CONFIG_FILE}")
config = None
with open(CONFIG_FILE, "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
log.setLevel(logging.DEBUG if config["debug"] else logging.INFO)
log.debug(f"Config: {config}")

IMGRESIZE_CHANNEL = config["imgresize_channel"]
YOLO_CHANNEL = config["yolo_channel"]
PLATECROP_CHANNEL = config["platecrop_channel"]
OCR_CHANNEL = config["ocr_channel"]
IMGCOLOR_CHANNEL = config["imgcolor_channel"]

INSECURE_PORTS = config["insecure_ports"]

imgresize_stub = imgresize_pb2_grpc.ImgResizeStub(
    grpc.insecure_channel(IMGRESIZE_CHANNEL)
)
yolo_stub = yolov8_pb2_grpc.Yolov8Stub(
    grpc.insecure_channel(YOLO_CHANNEL)
)
platecrop_stub = platecrop_pb2_grpc.PlateCropStub(
    grpc.insecure_channel(PLATECROP_CHANNEL)
)
ocr_stub = ocr_pb2_grpc.OcrStub(
    grpc.insecure_channel(OCR_CHANNEL)
)
imgcolor_stub = imgcolor_pb2_grpc.ImgColorStub(
    grpc.insecure_channel(IMGCOLOR_CHANNEL)
)

class IdentifyServicer(identify_pb2_grpc.IdentifyServicer):
    def Identify(self, request, context):
        start_time_total = time.perf_counter()
        # Unpack image
        img_str = request.data
        img = bts_to_img(img_str)
        # Resize
        (h, w) = img.shape[:2]
        start_time_resize = time.perf_counter()
        imgresize_response = imgresize_stub.To480p(types_pb2.Image(data=image_to_bts(img)))
        end_time_resize = time.perf_counter()
        elapsed_time_resize = round((end_time_resize - start_time_resize) * 1000, 2)
        log.info(f"TOTAL TIME RESIZE: {elapsed_time_resize} ms")
    
        
        tmp_img = bts_to_img(imgresize_response.data)
        # Detect boxes
        start_time = time.perf_counter()
        yolo_response = yolo_stub.Detect(types_pb2.Image(data=image_to_bts(tmp_img)))
        elapsed_time = round((time.perf_counter() - start_time) * 1000, 2)
        log.info(f"TOTAL TIME YOLO: {elapsed_time} ms")
        
        boxes = yolo_response.boxes
        # Crop to boxes
        box_ids = []
        box_imgs = []
        box_org = []
        for box in boxes:
            x0 = int(math.floor(box.x0 * w))
            y0 = int(math.floor(box.y0 * h))
            x1 = int(math.ceil(box.x1 * w))
            y1 = int(math.ceil(box.y1 * h))
            id = box.id
            if x1 < x0:
                x0, x1 = x1, x0
            if y1 < y0:
                y0, y1 = y1, y0
            cropped = img[y0:y1,x0:x1]
            box_ids.append(id)
            box_imgs.append(cropped)
            box_org.append((x0,y0,x1,y1))  
        # Extract plates
        plate_imgs = []
        box_colors = []
        
        
        start_time = time.perf_counter()
        for box_img in box_imgs:
            # print(box_img)
            request_img = types_pb2.Image(data=image_to_bts(box_img))
            platecrop_response = platecrop_stub.Crop(request_img)
            imgcolor_response = imgcolor_stub.GetPrimaryColors(request_img)
            plate_imgs.append(bts_to_img(platecrop_response.data))
            box_colors.append(",".join(list(imgcolor_response.text)))
        elapsed_time = round((time.perf_counter() - start_time) * 1000, 2)
        log.info(f"TOTAL TIME PLATECROP: {elapsed_time} ms")
        
        # Read text (ocr)
        start_time = time.perf_counter()
        vehicle_ids = []
        for plate_img in plate_imgs:
            platecrop_response = ocr_stub.ReadText(types_pb2.Image(data=image_to_bts(plate_img)))
            texts = platecrop_response.text
            vehicle_id = "#".join(texts)
            vehicle_ids.append(vehicle_id)
        elapsed_time = round((time.perf_counter() - start_time) * 1000, 2)
        log.info(f"TOTAL TIME OCR: {elapsed_time} ms")

        # Return response
        result = list()
        for i in range(len(boxes)):
            x0, y0, x1, y1 = box_org[i]
            # result.append({
            #     "id":f"{box_ids[i]}_{box_colors[i]}_{vehicle_ids[i]}",
            #     "x0": x0, "x1": x1, "y0": y0, "y1": y1
            # })
            result.append(
                types_pb2.Box(
                    x0=x0, x1=x1, y0=y0, y1=y1,
                    id = f"{box_ids[i]}_{box_colors[i]}_{vehicle_ids[i]}"
                )
            )
        response = types_pb2.VehicleIdentifyResult(
            vehicles=result
        )
        end_time_total = time.perf_counter()
        elapsed_time_total = round((end_time_total - start_time_total) * 1000, 2)
        log.info(f"TOTAL TIME IDENTIFY: {elapsed_time_total} ms")

        return response

def serve(silent:bool):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=config["n_threads"]))
    identify_pb2_grpc.add_IdentifyServicer_to_server(IdentifyServicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    log.info(f"[Identify] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)