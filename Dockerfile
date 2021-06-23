FROM python:alpine3.7
RUN apk add libxml2-utils
WORKDIR /app
COPY procsim/ procsim/
COPY setup.py .
COPY README.md .
RUN python3 /app/setup.py install
ENTRYPOINT ["procsim"]
