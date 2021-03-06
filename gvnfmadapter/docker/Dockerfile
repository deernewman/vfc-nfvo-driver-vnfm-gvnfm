FROM ubuntu:14.04

ARG HTTP_PROXY=${HTTP_PROXY}
ARG HTTPS_PROXY=${HTTPS_PROXY}

ENV http_proxy $HTTP_PROXY
ENV https_proxy $HTTPS_PROXY

RUN sed -i "s|set compatible|set nocompatible|" /etc/vim/vimrc.tiny
RUN echo "set backspace=2" >> /etc/vim/vimrc.tiny

RUN apt-get update && \
    apt-get install -y python-virtualenv && \
    apt-get install -y python-setuptools && \
    apt-get install -y python-dev && \
    apt-get install -y python-pip && \
    apt-get install -y gcc && \
    apt-get install -y wget && \
    apt-get install -y unzip && \
    apt-get install -y curl && \
    apt-get install -y build-essential && \
    apt-get install -y libssl-dev && \
    apt-get install -y libffi-dev

ADD . /service
WORKDIR /service

# get binary zip from nexus
RUN wget -q -O vfc-nfvo-driver-vnfm-gvnfm-gvnfmadapter.zip 'https://nexus.onap.org/service/local/artifact/maven/redirect?r=snapshots&g=org.onap.vfc.nfvo.driver.vnfm.gvnfm.gvnfmadapter&a=vfc-nfvo-driver-vnfm-gvnfm-gvnfmadapter&v=LATEST&e=zip' && \
    unzip vfc-nfvo-driver-vnfm-gvnfm-gvnfmadapter.zip && \
    rm -rf vfc-nfvo-driver-vnfm-gvnfm-gvnfmadapter.zip

WORKDIR /service/vfc/nfvo/driver/vnfm/gvnfm/gvnfmadapter
RUN pip install -r requirements.txt

EXPOSE 8484

WORKDIR /service
ENTRYPOINT vfc/nfvo/driver/vnfm/gvnfm/gvnfmadapter/docker/docker-entrypoint.sh
