FROM python:3.10-slim-buster
ADD App.py utils.py layout_servers.py requirements.txt /
COPY cvp-0.0.1.tar.gz .
RUN mkdir Estimators assets
ADD Estimators/ /Estimators
ADD assets/ /assets
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0
RUN pip install -r requirements.txt
RUN pip install cvp-0.0.1.tar.gz
# build with: docker build -t echo_img .
# run with: docker run --publish  4500:8050 --name echo_img_container echo_img