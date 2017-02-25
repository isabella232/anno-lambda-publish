#!/usr/bin/env python
# _*_ coding:utf-8 _*_
import os
import logging
import boto3
import gzip
from StringIO import StringIO
from jinja2 import Environment, FileSystemLoader

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

cwd = os.path.dirname(__file__)
TPL_ABS_PATH = os.path.abspath(os.path.join(cwd, '../code/templates'))
env = Environment(loader=FileSystemLoader(TPL_ABS_PATH))

s3 = boto3.resource('s3')
bucket = s3.Bucket('apps.npr.org')


def upload_template_contents(context, template, s3filename=None):
    """
    populates jinja2 template
    and uploads to s3
    """
    if not s3filename:
        s3filename = template
    template = env.get_template(template)
    markup = template.render(**context)
    logger.warning('markup: %s' % markup)
    f = StringIO()
    with gzip.GzipFile(fileobj=f, mode='w', mtime=0) as gz:
        gz.write(markup)
    # Reset buffer to beginning
    f.seek(0)
    s3Key = '%s/%s' % ('factchecks/preview', s3filename)
    bucket.put_object(Key=s3Key,
                      Body=f.read(),
                      ACL='public-read',
                      ContentType='text/html',
                      ContentEncoding='gzip',
                      CacheControl='max-age=%s' % 20)


def run():
    """
    """
    context = {}
    context['DEPLOYMENT_TARGET'] = 'production'
    context['FACTCHECKS_DIRECTORY_PREFIX'] = 'factchecks/'
    context['PRODUCTION_S3_BUCKET'] = 'apps.npr.org'
    context['CURRENT_FACTCHECK'] = 'preview'
    context['AUTOINIT_LOADER'] = False
    upload_template_contents(context, 'parent.html', 'index.html')


if __name__ == '__main__':
    run()
