FROM seguro/platform 

ENV MQTT_HOST=mosquitto
#check if this is required really
RUN mkdir /src
WORKDIR /src

COPY . /src
RUN pip install --no-cache-dir .
# ENTRYPOINT [ "/bin/bash" ]
CMD ["hb-mon-ui"]
