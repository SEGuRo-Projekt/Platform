FROM golang:1.20-alpine as builder

RUN  go install github.com/minio/mc@latest

FROM python:3.11

COPY --from=builder /go/bin/mc /usr/bin/mc

RUN pip install minio==7.1.14

RUN apt-get update && \
    apt-get install --yes openssh-client
