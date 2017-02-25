#!/usr/bin/env python
# _*_ coding:utf-8 _*_
import os
import logging
import boto3
from base64 import b64decode

kms = boto3.client('kms')
# env vars
SRC_BUCKET = os.environ.get('SRC_BUCKET')
SRC_ANNO_PATH = os.environ.get('SRC_ANNO_PATH')
DST_BUCKET = os.environ.get('DST_BUCKET')
DST_ANNO_PATH = os.environ.get('DST_ANNO_PATH')

#Global vars
DEFAULT_MAX_AGE = 20

LOG_FORMAT = '%(levelname)s:%(name)s:%(asctime)s: %(message)s'
LOG_LEVEL = logging.WARNING
