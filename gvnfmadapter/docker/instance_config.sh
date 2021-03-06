#!/bin/bash

MSB_IP=`echo $MSB_ADDR | cut -d: -f 1`
MSB_PORT=`echo $MSB_ADDR | cut -d: -f 2`

if [ $MSB_IP ]; then
    sed -i "s|MSB_SERVICE_IP.*|MSB_SERVICE_IP = '$MSB_IP'|" vfc/nfvo/driver/vnfm/gvnfm/gvnfmadapter/driver/pub/config/config.py
fi

if [ $MSB_PORT ]; then
    sed -i "s|MSB_SERVICE_PORT.*|MSB_SERVICE_PORT = '$MSB_PORT'|" vfc/nfvo/driver/vnfm/gvnfm/gvnfmadapter/driver/pub/config/config.py
fi

if [ $SERVICE_IP ]; then
    sed -i "s|\"ip\": \".*\"|\"ip\": \"$SERVICE_IP\"|" vfc/nfvo/driver/vnfm/gvnfm/gvnfmadapter/driver/pub/config/config.py
fi

cat vfc/nfvo/driver/vnfm/gvnfm/gvnfmadapter/driver/pub/config/config.py
