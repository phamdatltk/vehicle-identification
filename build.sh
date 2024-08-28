#!/bin/zsh
docker build --file ./dockerfile.identify -t jerapiblannett/vehicleidentify-identify:latest .
docker build --file ./docker/dockerfile.imgcolor -t jerapiblannett/vehicleidentify-imgcolor:latest .
docker build --file ./docker/dockerfile.imgresize -t jerapiblannett/vehicleidentify-imgresize:latest .
docker build --file ./docker/dockerfile.ocr -t jerapiblannett/vehicleidentify-ocr:latest .
docker build --file ./docker/dockerfile.platecrop -t jerapiblannett/vehicleidentify-platecrop:latest .
docker build --file ./docker/dockerfile.yolov8 -t jerapiblannett/vehicleidentify-yolo:latest .
docker build --file ./docker/dockerfile.webserver -t jerapiblannett/vehicleidentify-webserver:latest .

docker push jerapiblannett/vehicleidentify-identify:latest
docker push jerapiblannett/vehicleidentify-imgcolor:latest
docker push jerapiblannett/vehicleidentify-imgresize:latest
docker push jerapiblannett/vehicleidentify-ocr:latest
docker push jerapiblannett/vehicleidentify-platecrop:latest
docker push jerapiblannett/vehicleidentify-yolo:latest
docker push jerapiblannett/vehicleidentify-webserver:latest
