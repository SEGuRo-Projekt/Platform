/usr/bin/env sh

set -e

mc config host add minio http://minio:9000 ${S3_USER} ${S3_PASSWORD};
mc mb minio/seguro;
exit 0;