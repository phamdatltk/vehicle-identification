Write-Output "Building images..."
docker build --file .\docker\dockerfile.identify -t jerapiblannett/vehicleidentify-identify:latest .
docker build --file .\docker\dockerfile.imgcolor -t jerapiblannett/vehicleidentify-imgcolor:latest .
docker build --file .\docker\dockerfile.imgresize -t jerapiblannett/vehicleidentify-imgresize:latest .
docker build --file .\docker\dockerfile.ocr -t jerapiblannett/vehicleidentify-ocr:latest .
docker build --file .\docker\dockerfile.platecrop -t jerapiblannett/vehicleidentify-platecrop:latest .
docker build --file .\docker\dockerfile.yolo -t jerapiblannett/vehicleidentify-yolo:latest .
docker build --file .\docker\dockerfile.webserver -t jerapiblannett/vehicleidentify-webserver:latest .

Write-Output "Pushing to dockerhub..."
docker push jerapiblannett/vehicleidentify-identify:latest
docker push jerapiblannett/vehicleidentify-imgcolor:latest
docker push jerapiblannett/vehicleidentify-imgresize:latest
docker push jerapiblannett/vehicleidentify-ocr:latest
docker push jerapiblannett/vehicleidentify-platecrop:latest
docker push jerapiblannett/vehicleidentify-yolo:latest
docker push jerapiblannett/vehicleidentify-webserver:latest
