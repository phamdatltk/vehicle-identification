# Vehicle-Identification

This is a demo of how complex A.I. appication can be deployed as microservices on cloud environment. This project can be used as heavy and non-consistant load for load-balancing testbeds.

```mermaid
block-beta
columns 4
    YOUTUBE:1
    space
    block:user:2
    jmeter/postman:1
    locust/browser:1
    end
    space
    space
    space
    space
    block:App:4
    ResizeImage
    ExtractColor
    YOLO
    WebServer
    PlateCrop
    OCR
    Identify
    end
    space
    space
    space
    space
    gRPC:4
    ResizeImage --> gRPC
    ExtractColor --> gRPC
    YOLO --> gRPC
    PlateCrop --> gRPC
    OCR --> gRPC
    Identify --> gRPC
    WebServer --> gRPC
    gRPC --> ResizeImage
    gRPC --> ExtractColor
    gRPC --> YOLO
    gRPC --> PlateCrop
    gRPC --> OCR
    gRPC --> Identify
    gRPC --> WebServer
    locust/browser --> WebServer
    WebServer --"http"--> locust/browser
    jmeter/postman --> WebServer
    WebServer --"http"--> jmeter/postman
    YOUTUBE --> WebServer
    WebServer --"http"--> YOUTUBE
```

## Compile and start background services

### Docker

With `docker-compose`, compile and run are completed in a command.

```bash
# Build
docker-compose -f ./docker/compose.yaml build
# Run
docker-compose -f ./docker/compose.yaml up
```

### Kubernetes

First, create namespace `j12t-alpha` then execute the command:

```bash
kubectl apply -f ./k8s
```

Or just edit the `metadata.namespace` attribute in `k8s/*.yml`.

### Development environment

```bash
# work.in.progress...
sudo apt update -y && sudo apt upgrade -y
sudo apt install build-essential -y
sudo apt-get update && sudo apt-get install ffmpeg libsm6 libxext6 -y
pip install PIL vidgear easyocr numpy ultralytics matplotlib opencv --break-system-packages
```

## Run the application

### Client demo application

```bash
python Identify_Client.py
```

### Web server

By default, `WebServer` listens at port `8080`

API list:

| Endpoint                                                                       | Method | Request content-type | Response content-type                     |
|--------------------------------------------------------------------------------|--------|----------------------|-------------------------------------------|
| [/](#get-)                                                                     | GET    | None                 | text/html                                 |
| [/api/identify](#post-apiidentify)                                             | POST   | image/*              | image/png                                 |
| [/stream?url=`{{url}}`&quality=`{{quality}}`&noskip=`{{noskip}}`](#get-stream) | GET    | None                 | multipart/x-mixed-replace; boundary=frame |

## Sequence diagrams

### `GET: /`
```mermaid
sequenceDiagram
    USER->>+WebServer: GET:/
    WebServer->>-USER: html_document 
```

### `POST: /api/identify`
```mermaid
sequenceDiagram
    USER->>+WebServer: POST:/api/identify:image
    WebServer->>+ImgResize: ResizeImage(image)
    ImgResize->>-WebServer: image_at_480p
    WebServer->>+YOLO: FindBoxes(image_at_480p)
    YOLO->>-WebServer: boxes
    WebServer->>+WebServer: CropToBoxes(image, boxes)
    WebServer->>-WebServer: image_boxes
    WebServer->>+ExtractColor: ExtractColor(image_boxes)
    ExtractColor->>-WebServer: main_colors
    WebServer->>+PlateCrop: CropToPlate(image_boxes)
    PlateCrop->>-WebServer: image_plates
    WebServer->>+OCR: ReadText(image_plates)
    OCR->>-WebServer: texts
    WebServer->>+WebServer: Render(image, boxes, texts)
    WebServer->>-WebServer: annotated_image
    WebServer->>-USER: annotated_image
```

### `GET: /stream`
```mermaid
sequenceDiagram
    USER->>+WebServer: GET:/stream?url={url}&quality={quality}&noskip={noskip}
    WebServer->>+YOUTUBE: get_video_stream(url)
    YOUTUBE->>-WebServer: video_stream
    loop feed
    WebServer->>+WebServer: get_frame(video_stream)
    WebServer->>-WebServer: frame
    WebServer->>+ImgResize: ResizeImage(frame)
    ImgResize->>-WebServer: frame_at_480p
    WebServer->>+YOLO: FindBoxes(frame_at_480p)
    YOLO->>-WebServer: boxes
    WebServer->>+WebServer: CropToBoxes(frame, boxes)
    WebServer->>-WebServer: frame_boxes
    WebServer->>+ExtractColor: ExtractColor(frame_boxes)
    ExtractColor->>-WebServer: main_colors
    WebServer->>+PlateCrop: CropToPlate(frame_boxes)
    PlateCrop->>-WebServer: frame_plates
    WebServer->>+OCR: ReadText(frame_plates)
    OCR->>-WebServer: texts
    WebServer->>+WebServer: Render(frame, boxes, texts)
    WebServer->>-WebServer: annotated_frame
    WebServer->>-USER: annotated_frame
    end
```