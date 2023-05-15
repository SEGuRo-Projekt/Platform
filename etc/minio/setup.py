#!/usr/bin/env python

import os
import logging
import minio
from pprint import pformat

def main():
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s', level=logging.INFO)

    minio_user = os.environ.get('MINIO_ROOT_USER')
    minio_pass = os.environ.get('MINIO_ROOT_PASSWORD')
    minio_endpoint = 'minio:9000'
    minio_url = f'http://{minio_endpoint}'

    logging.info('Create SSH host key')
    os.system('ssh-keygen -q -N "" -t rsa -b 4096 -f /keys/ssh_host_rsa_key')

    logging.info('Create host alias')
    os.system(f'mc config host add minio {minio_url} {minio_user} {minio_pass}')

    mc = minio.Minio(minio_endpoint, minio_user, minio_pass, secure=False)
    mca = minio.MinioAdmin(target='minio')

    logging.info('Server info: %s', pformat(mca.info()))

    if mc.bucket_exists('seguro'):
        logging.info('Bucket already exists')
    else:
        logging.info('Creating bucket:')
        mc.make_bucket('seguro')

if __name__ == '__main__':
    main()
