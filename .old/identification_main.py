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

from utills import drawText

yolo_model = YOLO(verbose=False)
ocr_model = easyocr.Reader(["en","vi"], verbose=False, model_storage_directory=".")

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = WPODNet()
model.to(device)
checkpoint = torch.load('./wpodnet.pth')
model.load_state_dict(checkpoint)
wpod_model = Predictor(model)

def VehicleDetect(img) -> list[dict]:
    # Resize to 480p ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <image> data=bytes,metadata=bytes
    (h, w) = img.shape[:2]
    new_height = 480
    aspect_ratio = w/h
    new_width = int(new_height * aspect_ratio)
    tmp_img = cv2.resize(img, (new_width, new_height))
    
    # Detect boxes & raw id ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <detectresult> x0=array[int],x1=array[int],y0=array[int],y1=array[int],id=array[string]
    detect_results = yolo_model.track(tmp_img, verbose=False)
    boxes = detect_results[0].boxes
    n_fig =len(boxes)
    vehicles_box = []
    vehicles_id = []
    for box in boxes:
        x0, y0, x1, y1 = box.xyxyn[0]
        id = "#"
        if not (box.id is None):
            id = box.id[0]
        vehicles_id.append(f"{id}_{detect_results[0].names[int(round(box.cls[0].item()))]}")
        vehicles_box.append((x0, y0, x1, y1))
        
    # Crop to boxes ----> local
    vehicles_img = []
    vehicles_box_org = []
    for box in vehicles_box:
        x0, y0, x1, y1 = box
        x0 = int(x0*w)
        x1 = int(x1*w)
        y0 = int(y0*h)
        y1 = int(y1*h)
        cropped = img[y0:y1,x0:x1]
        vehicles_img.append(cropped)
        vehicles_box_org.append((x0, y0, x1, y1))
        
    # Extract plates (if possible) ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <image> data=bytes,metadata=bytes
    plates = []
    for v_img in vehicles_img:
        prediction = wpod_model.predict(Image.fromarray(np.uint8(v_img)).convert('RGB'))
        wrapped = prediction.warp()
        if prediction.confidence > 0.9:
            plates.append(np.array(wrapped))
        else:
            plates.append(v_img)
    
    # Read text ----> remote
    # Input  : <image> data=bytes,metadata=bytes
    # Output : <string>
    vehicles_iden = []
    for v_img in plates:
        ocr_result = ocr_model.readtext(v_img, paragraph=True, detail=0)
        vehicles_iden.append("#&#".join(ocr_result)  if len(ocr_result) > 0 else "##&NOTEXT&##")
    
    # Result ----> local
    result = list()
    for i in range(n_fig):
        x0, y0, x1, y1 = vehicles_box_org[i]
        result.append({
            "id":f"{vehicles_id[i]}_{vehicles_iden[i]}",
            "x0": x0, "x1": x1, "y0": y0, "y1": y1
        })
        
    return result

options = {
    "STREAM_RESOLUTION": "1080p",
    "THREAD_TIMEOUT": 30,
    "CAP_PROP_FPS": 15,
    'THREADED_QUEUE_MODE': False
}

def IdentifyFromStream(src):
    capture = vidgear.gears.CamGear(src, stream_mode=True, logging=False, **options).start()
    
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
        
        # Resize to 900p
        (h, w) = frame.shape[:2]
        new_height = 900
        aspect_ratio = w/h
        new_width = int(new_height * aspect_ratio)
        frame = cv2.resize(frame, (new_width, new_height))
        
        st = time.perf_counter() - st
        
        st = round(st*1000)
        
        frame = drawText(
                frame, f"{dtr} @ {st}ms",
                text_position=(0,0), 
                text_color=(255,0,0)
            )
        
        cv2.imshow("Output", frame)
        
        with open("./detect.log", "at") as f:
            f.write(f"{capture.ytv_metadata['id']}, {dtr}, {idens}\n")
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
    # safely close video stream
    capture.stop()

    # close output window
    cv2.destroyAllWindows()
    
if __name__=="__main__":
    with open("./detect.log", "wt") as f:
        f.write("youtube_id, datetime, identity_infos\n")

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
    proc2.start()
    proc3.start()
    proc1.join()
    proc2.join()
    proc3.join()
    # IdentifyFromStream("https://www.youtube.com/watch?v=7HaJArMDKgI")
    # IdentifyFromStream("https://www.youtube.com/watch?v=KBsqQez-O4w")
    # IdentifyFromStream("https://www.youtube.com/watch?v=MNn9qKG2UFI")

