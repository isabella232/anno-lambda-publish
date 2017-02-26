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
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

env = Environment(loader=FileSystemLoader('templates'))


def copy_stage_to_prod():
    """
    copy recursively changing the acl accordingly
    """
    s3_src = "s3://%s/%s%s" % (
        app_config.SRC_BUCKET,
        app_config.FACTCHECKS_DIRECTORY_PREFIX,
        app_config.PREVIEW_FACTCHECK)
    s3_dst = "s3://%s/%s%s" % (
        app_config.DST_BUCKET,
        app_config.FACTCHECKS_DIRECTORY_PREFIX,
        app_config.CURRENT_FACTCHECK)
    command = ['./aws', 's3', 'cp', '--acl', 'public-read', '--recursive',
               '--quiet', s3_src, s3_dst]
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT)
        logger.info('Copied recursively from stage')
    except subprocess.CalledProcessError, e:
        logger.error(e.output)
        raise e


def make_context():
    """
    make required context from app_config
    """
    context = {}
    context['DEPLOYMENT_TARGET'] = app_config.DEPLOYMENT_TARGET
    context['FACTCHECKS_DIRECTORY_PREFIX'] = app_config.FACTCHECKS_DIRECTORY_PREFIX
    context['PRODUCTION_S3_BUCKET'] = app_config.DST_BUCKET
    context['CURRENT_FACTCHECK'] = app_config.CURRENT_FACTCHECK
    context['AUTOINIT_LOADER'] = app_config.AUTOINIT_LOADER
    return context


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
    dst_bucket = s3.Bucket(app_config.DST_BUCKET)
    dst_key = '%s/%s/%s' % (
        app_config.FACTCHECKS_DIRECTORY_PREFIX,
        app_config.CURRENT_FACTCHECK,
        s3filename)
    dst_bucket.put_object(Key=dst_key,
                          Body=f.read(),
                          ContentType='text/html',
                          ContentEncoding='gzip',
                          CacheControl='max-age=%s' % app_config.DEFAULT_MAX_AGE)


def lambda_handler(event, context):
    """
    authomatic access to google docs
    """
    try:
        logger.info('Start publishing factcheck')
        # Copy recursively from staging to production changing acl
        copy_stage_to_prod()
        # Generate required context for template
        context = make_context()
        # Generate final files and upload to S3
        upload_template_contents(context, 'parent.html', 'index.html')
        logger.info('Generated new index template. Execution successful')
        return True
    except Exception, e:
        logger.error('Failed execution of lambda function. reason: %s' % (e))
        return False
