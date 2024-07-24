FROM amazon/aws-lambda-python:3.9

# Install chrome dependencies
RUN yum install -y atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm jq unzip
RUN yum install -y zlib-devel libjpeg-devel gcc make glibc-devel git

# Copy and run the chrome installer script
COPY ./chrome-installer.sh ./chrome-installer.sh
COPY ./requirements.txt ./requirements.txt
COPY ./extractor_lambda.py ./extractor_lambda.py
COPY ./models ./models
RUN chmod +x ./chrome-installer.sh
RUN ./chrome-installer.sh
RUN rm ./chrome-installer.sh
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application code
COPY image_hashing_storage_lambda.py ./
# Command to run the Lambda function
CMD [ "image_hashing_storage_lambda.lambda_handler" ]