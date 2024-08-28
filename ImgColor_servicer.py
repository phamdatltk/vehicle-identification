import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import grpc
from concurrent import futures
from sklearn.cluster import KMeans
from skimage.color import rgb2lab, deltaE_cie76
from collections import Counter
import yaml

import protos.imgcolor_pb2_grpc as imgcolor_pb2_grpc
import protos.imgcolor_pb2 as imgcolor_pb2
import protos.types_pb2 as types_pb2

from utills import bts_to_img, image_to_bts, rgb_to_hex, closest_color

config = None
with open("./config/ImgColorService.yml", "rt") as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
    
INSECURE_PORTS = config["insecure_ports"]

class ImgColorServicer(imgcolor_pb2_grpc.ImgColorServicer):
    def GetPrimaryColors(self, request, context):
        img_bts = request.data
        img = bts_to_img(img_bts)
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        #Reduce the input to two dimensions for KMeans
        mod_img = img.reshape(img.shape[0]*img.shape[1], 3)

        #Define the clusters
        clf = KMeans(n_clusters = 3)
        labels = clf.fit_predict(mod_img)

        counts = Counter(labels)
        counts = dict(sorted(counts.items(), reverse=True))

        center_colours = clf.cluster_centers_
        ordered_colours = [center_colours[i] for i in counts.keys()]
        # hex_colours = [rgb_to_hex(ordered_colours[i]) for i in counts.keys()]
        rgb_colours = [ordered_colours[i] for i in counts.keys()]
        color_names = [closest_color(c) for c in rgb_colours]
        response = types_pb2.ImgColorsResult(
            text=color_names
        )
        return response

def serve(silent:bool):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    imgcolor_pb2_grpc.add_ImgColorServicer_to_server(ImgColorServicer(), server)
    for p in INSECURE_PORTS:
        server.add_insecure_port(p)
    server.start()
    print(f"[ImgColor] ports: {INSECURE_PORTS}")
    server.wait_for_termination()
    
if __name__=="__main__":
    serve(True)