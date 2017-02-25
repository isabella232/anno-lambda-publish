#!/usr/bin/env python
# _*_ coding:utf-8 _*_
import logging
import subprocess
import boto3
import gzip
from StringIO import StringIO
from jinja2 import Environment, FileSystemLoader
import app_config


s3 = boto3.resource('s3')

logger = logging.getLogger()
logger.setLevel(app_config.LOG_LEVEL)

env = Environment(loader=FileSystemLoader('templates'))


def copy_stage_to_prod():
    """
    copy recursively changing the acl accordingly
    """
    src_bucket = s3.Bucket(app_config.SRC_BUCKET)
    dst_bucket = s3.Bucket(app_config.DST_BUCKET)
    s3_src = 's3://%s/%s/%s' % (
        src_bucket,
        app_config.FACTCHECKS_DIRECTORY_PREFIX,
        app_config.PREVIEW_FACTCHECK)
    s3_dst = 's3://%s/%s/%s' % (
        dst_bucket,
        app_config.FACTCHECKS_DIRECTORY_PREFIX,
        app_config.CURRENT_FACTCHECK)
    command = ['./aws', 's3', 'cp', '--acl', 'public-read', '--recursive',
               s3_src, s3_dst]
    logger.info(subprocess.check_output(command, stderr=subprocess.STDOUT))


def upload_template_contents(context, template, s3filename=None):
    """
    populates jinja2 template
    and uploads to s3
    """
    if not s3filename:
        s3filename = template
    template = env.get_template(template)
    markup = template.render(**context)
    f = StringIO()
    with gzip.GzipFile(fileobj=f, mode='w', mtime=0) as gz:
        gz.write(markup)
    # Reset buffer to beginning
    f.seek(0)
    s3Key = '%s/%s' % (app_config.DST_ANNO_PATH, s3filename)
    bucket.put_object(Key=s3Key,
                      Body=f.read(),
                      ContentType='text/html',
                      ContentEncoding='gzip',
                      CacheControl='max-age=%s' % app_config.DEFAULT_MAX_AGE)


def lambda_handler(event, context):
    """
    authomatic access to google docs
    """
    #TODO
    # Copy recursively from staging to production changing acl
    copy_stage_to_prod()
    # Generate required context for template
    # Generate final files and upload to S3
    upload_template_contents(context, 'parent.html', 'index.html')
