#!/bin/bash
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

set -e

PKI_CLIENT_CERTS="mp1 mp2 admin"
PKI_SUBJECT="/C=DE/ST=NRW/L=Aachen/O=OPAL-RT Germany GmbH/OU=Research and Development"
PKI_KEY_TYPE="rsa:4096"
PKI_EXPIRY_DAYS=3650

function create_ssh_keys() {
  echo "== Creating SSH host key..."
  ssh-keygen -N '' -t rsa -b 4096 -f /keys/ssh_host_rsa_key
  echo "Public host key: $(cat /keys/ssh_host_rsa_key.pub)"
  echo
}

function create_pki_ca() {
  echo "=== Creating CA certificate"
  openssl req \
    -x509 \
    -new \
    -nodes \
    -sha256 \
    -days ${PKI_EXPIRY_DAYS} \
    -newkey ${PKI_KEY_TYPE} \
    -keyout /keys/ca.key \
    -out /certs/ca.crt \
    -subj "${PKI_SUBJECT}/CN=SEGuRo Certificate Authority" 2> /dev/null
}

function create_pki_server() {
  echo "=== Creating server certificate"
  cat > server.v3.ext << EOF
authorityKeyIdentifier = keyid, issuer
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}

# For platform internal communication only
DNS.3 = minio
DNS.4 = mosquitto
EOF

  openssl req \
    -new \
    -nodes \
    -out server.csr \
    -newkey ${PKI_KEY_TYPE} \
    -keyout /keys/server.key \
    -subj "${PKI_SUBJECT}/CN=Server Certificate" 2> /dev/null

  openssl x509 \
    -req \
    -days ${PKI_EXPIRY_DAYS} \
    -sha256 \
    -extfile server.v3.ext \
    -CA /certs/ca.crt \
    -CAkey /keys/ca.key \
    -CAcreateserial \
    -in server.csr \
    -out /certs/server.crt 2> /dev/null
}

function create_pki_client() {
  CN=$1

  echo "=== Creating client certificate for ${CN}"
  cat > client.v3.ext << EOF
authorityKeyIdentifier = keyid, issuer
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = clientAuth
EOF

  openssl req \
    -new \
    -nodes \
    -out client-${CN}.csr \
    -newkey ${PKI_KEY_TYPE} \
    -keyout /keys/client-${CN}.key \
    -subj "${PKI_SUBJECT}/CN=${CN}" 2> /dev/null

  openssl x509 \
    -req \
    -days ${PKI_EXPIRY_DAYS} \
    -sha256 \
    -extfile client.v3.ext \
    -CA /certs/ca.crt \
    -CAkey /keys/ca.key \
    -CAcreateserial \
    -in client-${CN}.csr \
    -out /certs/client-${CN}.crt 2> /dev/null
}

if [ ${SECRET} == "PLEASE-CHANGE-ME" ]; then
  echo "Please change the value of the envvar SECRET in your .env file."
  exit -1
fi

if ! [ -f /keys/ssh_host_rsa_key ]; then
  create_ssh_keys
fi

echo "== Checking PKI certificates..."
[ -f /certs/ca.crt -a -f /keys/ca.key ] || \
create_pki_ca

[ -f /certs/server.crt -a -f /keys/server.key ] || \
create_pki_server

for CN in ${PKI_CLIENT_CERTS}; do
  [ -f /certs/client-${CN}.crt -a -f /keys/client-${CN}.key ] || \
  create_pki_client ${CN}
done

# Copy clients certs to user accessible mount
cp /certs/client-*.crt /keys/client-*.key /certs/ca.crt /keys/ca.key /keys-out/
chmod go+r /keys-out/*

# Prepare Minio keys
# See: https://min.io/docs/minio/linux/operations/network-encryption.html
mkdir -p /keys/minio/CAs
cp /certs/ca.crt /keys/minio/CAs
cp /certs/server.crt /keys/minio/public.crt
cp /keys/server.key /keys/minio/private.key

echo "== Managing htpasswd for registry..."
if [ -f /keys/registry_htpasswd ]; then
  if htpasswd -iv /keys/registry_htpasswd "${ADMIN_USERNAME}" <<< "${ADMIN_PASSWORD}" 2> /dev/null; then
    echo "Admin password unchanged"
  else
    htpasswd -iB /keys/registry_htpasswd "${ADMIN_USERNAME}" <<< "${ADMIN_PASSWORD}"
  fi
else
  htpasswd -iBc /keys/registry_htpasswd "${ADMIN_USERNAME}" <<< "${ADMIN_PASSWORD}"
fi
