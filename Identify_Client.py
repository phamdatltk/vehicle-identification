import os

import vidgear.gears
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
import grpc
import random
import datetime
import time
import multiprocessing as mp

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

DEV_ENV = False
if os.path.exists("./.env_dev"):
    DEV_ENV = True
    
IDENTIFY_CHANNEL = "localhost:50000"

identify_stub = identify_pb2_grpc.IdentifyStub(
    grpc.insecure_channel(IDENTIFY_CHANNEL)
)

input_stream_options = {
    "STREAM_RESOLUTION": "1080p",
    "THREAD_TIMEOUT": 30,
    "CAP_PROP_FPS": 15,
    'THREADED_QUEUE_MODE': True
}

def IdentifyFromStream(src):
    capture = vidgear.gears.CamGear(src, stream_mode=True, logging=False, **input_stream_options).start()
    
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
        
        with open("./data/detect.log", "at", encoding='utf-8') as f:
            f.write(f"{cap_id}, {dtr}, {frame_id},{idens}\n")
                
        # record.write(frame)
        cv2.imwrite(f"./data/{cap_id}/{frame_id}.png", frame)
        
        if DEV_ENV:
            # Resize to 900p
            (h, w) = frame.shape[:2]
            new_height = 600
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
    proc2.start()
    proc3.start()
    proc1.join()
    proc2.join()
    proc3.join()