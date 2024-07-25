FROM amazon/aws-lambda-python:3.8

RUN yum install -y nano git build-essential libglib2.0-0 libsm6 libxext6 libxrender-dev python3 python3-pip python3-opencv wget cmake ffmpeg libgl1

# Detectron2 prerequisites
RUN pip install -U torch==1.8.1+cpu torchvision==0.9.1+cpu -f https://download.pytorch.org/whl/torch_stable.html

# Detectron2 - CPU
RUN pip install -U detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cpu/torch1.8/index.html
RUN pip install -U cython \
	flask \
	flask-cors \
	requests \
	opencv-python-headless \
	Image \
	piexif \
	textblob \
	pyyaml \
	numpy \
;

COPY ./requirements.txt ./requirements.txt
COPY ./models ./models
RUN pip install -r requirements.txt

# Copy the main application code
COPY image_hashing_storage_lambda.py ./
# Command to run the Lambda function
CMD [ "image_hashing_storage_lambda.lambda_handler" ]