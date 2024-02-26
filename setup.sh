#!/bin/bash
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

if ! [ -f /keys/ssh_host_rsa_key ]; then
  echo "== Creating SSH host key..."
  ssh-keygen -N '' -t rsa -b 4096 -f /keys/ssh_host_rsa_key
  echo "Public host key: $(cat /keys/ssh_host_rsa_key.pub)"
  echo
fi

if ! [ -f /keys/server.crt -a -f /keys/server.key ]; then
  echo "== Creating self-signed server cert..."
  openssl req \
    -nodes \
    -x509 \
    -sha256 \
    -newkey rsa:4096 \
    -keyout /keys/server.key \
    -out /keys/server.crt \
    -days 3560 \
    -subj "/C=DE/ST=NRW/L=Aachen/O=OPAL-RT/OU=RnD/CN=localhost" \
    -addext "subjectAltName = DNS:*.localhost,DNS:localhost,DNS:*.seguro,DNS:seguro" > /dev/null

  openssl x509 -in /keys/server.crt -text -noout
  echo
fi

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
