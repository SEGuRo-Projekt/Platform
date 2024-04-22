#!/bin/bash
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

set -e

# Default values
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-s3gur0herne}

TLS_CACERT=${TLS_CACERT:-keys/ca.crt}
TLS_KEY=${TLS_KEY:-keys/client-admin.key}
TLS_CERT=${TLS_CERT:-keys/client-admin.crt}

S3_HOST=${S3_HOST:-localhost}
S3_PORT=${S3_PORT:-9000}
S3_BUCKET=${S3_BUCKET:-seguro}

BUCKETS="${S3_BUCKET} registry"

echo "== Setup Minio CLI with static credentials"
mkdir -p ~/.mc/certs/CAs
cp "${TLS_CACERT}" ~/.mc/certs/CAs/

export MC_HOST_minio="https://${ADMIN_USERNAME}:${ADMIN_PASSWORD}@${S3_HOST}:${S3_PORT}"

echo "== Create admin policy"
CN=$(openssl x509 -noout -subject -nameopt multiline -in "${TLS_CERT}" | sed -n 's/ *commonName *= *//p')
mc admin policy create minio "${CN}" <(cat <<-END
{
    "Version": "2012-10-17",
    "Statement": [
        {
             "Action": ["admin:*"],
             "Effect": "Allow"
        },
        {
            "Action": ["s3:*"],
            "Effect": "Allow",
            "Resource": "arn:aws:s3:::*"
        }
    ]
}
END
)

echo "== Setup Minio CLI with certificate credentials"
CREDS_RESPONSE=$(curl --request POST \
     --silent \
     --key "${TLS_KEY}" --cert "${TLS_CERT}" --cacert "${TLS_CACERT}" \
     "https://${S3_HOST}:${S3_PORT}?Action=AssumeRoleWithCertificate&Version=2011-06-15&DurationSeconds=3600")

ACCESS_KEY=$(sed -n 's/.*<AccessKeyId>\(.*\)<\/AccessKeyId>.*/\1/p' <<< "${CREDS_RESPONSE}")
SECRET_KEY=$(sed -n 's/.*<SecretAccessKey>\(.*\)<\/SecretAccessKey>.*/\1/p' <<< "${CREDS_RESPONSE}")
SESSION_TOKEN=$(sed -n 's/.*<SessionToken>\(.*\)<\/SessionToken>.*/\1/p' <<< "${CREDS_RESPONSE}")

export MC_HOST_minio="https://${ACCESS_KEY}:${SECRET_KEY}:${SESSION_TOKEN}@${S3_HOST}:${S3_PORT}"

echo "== Create buckets"
for BUCKET in ${BUCKETS}; do
    mc mb --ignore-existing "minio/${BUCKET}"
done

echo "== Buckets:"
mc ls minio

echo "== Policies:"
mc admin policy ls minio
