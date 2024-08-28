import os

import vidgear.gears
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import PIL.Image
from ultralytics import YOLO
import numpy as np
import cv2
import easyocr
import matplotlib.pyplot as plt
import math
import PIL
import vidgear
import random
import time
import datetime
from wpodnet.backend import Predictor
from wpodnet.model import WPODNet
import torch
from PIL import Image
import multiprocessing as mp
import grpc

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

from utills import drawText, bts_to_img, image_to_bts

DEV_ENV = False
if os.path.exists("./.env_dev"):
    DEV_ENV = True

# yolo_model = YOLO(verbose=False)
# ocr_model = easyocr.Reader(["en","vi"], verbose=False, model_storage_directory=".")

# device = 'cuda' if torch.cuda.is_available() else 'cpu'
# model = WPODNet()
# model.to(device)
# checkpoint = torch.load('./wpodnet.pth')
# model.load_state_dict(checkpoint)
# wpod_model = Predictor(model)

IMGRESIZE_CHANNEL = "localhost:50051"
YOLO_CHANNEL = "localhost:50052"
PLATECROP_CHANNEL = "localhost:50053"
OCR_CHANNEL = "localhost:50054"
IMGCOLOR_CHANNEL = "localhost:50055"

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

def VehicleDetect(img) -> list[dict]:
    # Resize to 480p ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <image> data=bytes,metadata=bytes
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    (h, w) = img.shape[:2]
    # new_height = 480
    # aspect_ratio = w/h
    # new_width = int(new_height * aspect_ratio)
    # tmp_img = cv2.resize(img, (new_width, new_height))
    
    platecrop_response = imgresize_stub.To480p(types_pb2.Image(data=image_to_bts(img)))
    tmp_img = bts_to_img(platecrop_response.data)
    
    # Detect boxes & raw id ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <detectresult> x0=array[int],x1=array[int],y0=array[int],y1=array[int],id=array[string]    
    # detect_results = yolo_model.track(tmp_img, verbose=False)
    # boxes = detect_results[0].boxes
    # n_fig =len(boxes)
    # vehicles_box = []
    # vehicles_id = []
    # for box in boxes:
    #     x0, y0, x1, y1 = box.xyxyn[0]
    #     id = "#"
    #     if not (box.id is None):
    #         id = box.id[0]
    #     vehicles_id.append(f"{id}_{detect_results[0].names[int(round(box.cls[0].item()))]}")
    #     vehicles_box.append((x0, y0, x1, y1))
    platecrop_response = yolo_stub.Detect(types_pb2.Image(data=image_to_bts(tmp_img)))
    boxes = platecrop_response.boxes
    
    # Crop to boxes ----> local
    # vehicles_img = []
    # vehicles_box_org = []
    # for box in vehicles_box:
    #     x0, y0, x1, y1 = box
    #     x0 = int(x0*w)
    #     x1 = int(x1*w)
    #     y0 = int(y0*h)
    #     y1 = int(y1*h)
    #     cropped = img[y0:y1,x0:x1]
    #     vehicles_img.append(cropped)
    #     vehicles_box_org.append((x0, y0, x1, y1))
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
        # print(cropped,id)
        box_org.append((x0,y0,x1,y1))    
    # Extract plates (if possible) ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <image> data=bytes,metadata=bytes
    # plates = []
    # for v_img in vehicles_img:
    #     prediction = wpod_model.predict(Image.fromarray(np.uint8(v_img)).convert('RGB'))
    #     wrapped = prediction.warp()
    #     if prediction.confidence > 0.9:
    #         plates.append(np.array(wrapped))
    #     else:
    #         plates.append(v_img)
    plate_imgs = []
    box_colors = []
    for box_img in box_imgs:
        # print(box_img)
        request_img = types_pb2.Image(data=image_to_bts(box_img))
        platecrop_response = platecrop_stub.Crop(request_img)
        imgcolor_response = imgcolor_stub.GetPrimaryColors(request_img)
        plate_imgs.append(bts_to_img(platecrop_response.data))
        box_colors.append(",".join(list(imgcolor_response.text)))
    
    # Read text ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <string>
    # vehicles_iden = []
    # for v_img in plates:
    #     ocr_result = ocr_model.readtext(v_img, paragraph=True, detail=0)
    #     vehicles_iden.append("#&#".join(ocr_result)  if len(ocr_result) > 0 else "##&NOTEXT&##")
    vehicle_ids = []
    for plate_img in plate_imgs:
        platecrop_response = ocr_stub.ReadText(types_pb2.Image(data=image_to_bts(plate_img)))
        texts = platecrop_response.text
        vehicle_id = "#".join(texts)
        vehicle_ids.append(vehicle_id)
    
    # Result ----> local
    result = list()
    for i in range(len(boxes)):
        x0, y0, x1, y1 = box_org[i]
        result.append({
            "id":f"{box_ids[i]}_{box_colors[i]}_{vehicle_ids[i]}",
            "x0": x0, "x1": x1, "y0": y0, "y1": y1
        })
        
    return result

options = {
    "STREAM_RESOLUTION": "1080p",
    "THREAD_TIMEOUT": 30,
    "CAP_PROP_FPS": 15,
    'THREADED_QUEUE_MODE': True
}

def IdentifyFromStream(src):
    capture = vidgear.gears.CamGear(src, stream_mode=True, logging=False, **options).start()
    # record = cv2.VideoWriter(f"./data/{capture.ytv_metadata['id']}.avi",cv2.VideoWriter_fourcc('M','J','P','G'),30,(1080,1920))
        
    cap_id = str(capture.ytv_metadata['id'])
    if not os.path.exists(f"./data/{cap_id}"):
        os.makedirs(f"./data/{cap_id}")

    frame_id = 0
    while True:
        frame = capture.read()
        dtr = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        st = time.perf_counter()
        
        if frame is None:
            break
        
        idens = VehicleDetect(frame)
        
        for iden in idens:
            color_code = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
            cv2.rectangle(
                frame, 
                (iden["x0"], iden["y0"]), (iden["x1"], iden["y1"]), 
                color=color_code, 
                thickness=2
            )
            
            frame = drawText(
                frame, iden["id"],
                text_position=(iden["x0"], iden["y0"]), 
                text_color=color_code
            )
        
        st = time.perf_counter() - st
        
        st = round(st*1000)
        
        frame = drawText(
                frame, f"{dtr} @ {st}ms",
                text_position=(0,0), 
                text_color=(255,0,0)
            )
        
        with open("./data/detect.log", "at", encoding='utf-8') as f:
            f.write(f"{cap_id}, {dtr}, {frame_id},{idens}\n")
                
        # record.write(frame)
        cv2.imwrite(f"./data/{cap_id}/{frame_id}.png", frame)
        
        if DEV_ENV:
            # Resize to 900p
            (h, w) = frame.shape[:2]
            new_height = 900
            aspect_ratio = w/h
            new_width = int(new_height * aspect_ratio)
            frame = cv2.resize(frame, (new_width, new_height))
            cv2.imshow(f"Output: {cap_id}", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
        frame_id += 1
    # safely close video stream
    capture.stop()
    # record.release()

    # close output window
    cv2.destroyAllWindows()
    
if __name__=="__main__":
    with open("./data/detect.log", "wt", encoding='utf-8') as f:
        f.write("youtube_id, datetime, frame_id, identity_infos\n")

    proc1 = mp.Process(
        target=IdentifyFromStream,
        args=("https://www.youtube.com/watch?v=7HaJArMDKgI",)
    )
    proc2 = mp.Process(
        target=IdentifyFromStream,
        args=("https://www.youtube.com/watch?v=KBsqQez-O4w",)
    )
    proc3 = mp.Process(
        target=IdentifyFromStream,
        args=("https://www.youtube.com/watch?v=MNn9qKG2UFI",)
    )
    proc1.start()
    # proc2.start()
    # proc3.start()
    proc1.join()
    # proc2.join()
    # proc3.join()
    # IdentifyFromStream("https://www.youtube.com/watch?v=7HaJArMDKgI")
    # IdentifyFromStream("https://www.youtube.com/watch?v=KBsqQez-O4w")
    # IdentifyFromStream("https://www.youtube.com/watch?v=MNn9qKG2UFI")

