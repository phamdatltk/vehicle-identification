import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from concurrent import futures
import cv2
import math
import grpc
import yaml

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

config = None
with open("./config/IdentifyService.yml", "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)

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
        # Unpack image
        img_str = request.data
        img = bts_to_img(img_str)
        # Resize
        (h, w) = img.shape[:2]
        imgresize_response = imgresize_stub.To480p(types_pb2.Image(data=image_to_bts(img)))
        tmp_img = bts_to_img(imgresize_response.data)
        # Detect boxes
        yolo_response = yolo_stub.Detect(types_pb2.Image(data=image_to_bts(tmp_img)))
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
        for box_img in box_imgs:
            # print(box_img)
            request_img = types_pb2.Image(data=image_to_bts(box_img))
            platecrop_response = platecrop_stub.Crop(request_img)
            imgcolor_response = imgcolor_stub.GetPrimaryColors(request_img)
            plate_imgs.append(bts_to_img(platecrop_response.data))
            box_colors.append(",".join(list(imgcolor_response.text)))
        # Read text (ocr)
        vehicle_ids = []
        for plate_img in plate_imgs:
            platecrop_response = ocr_stub.ReadText(types_pb2.Image(data=image_to_bts(plate_img)))
            texts = platecrop_response.text
            vehicle_id = "#".join(texts)
            vehicle_ids.append(vehicle_id)
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
        return response

def serve(silent:bool):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    identify_pb2_grpc.add_IdentifyServicer_to_server(IdentifyServicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    print(f"[Identify] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)