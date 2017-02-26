#!/usr/bin/env python
# _*_ coding:utf-8 _*_
from fabric.api import local, lcd, prefix, task, execute, quiet
from contextlib import contextmanager as _contextmanager
import os
import logging
import zipfile

"""
Logging
"""
LOG_FORMAT = '%(levelname)s:%(name)s:%(asctime)s: %(message)s'
LOG_LEVEL = logging.INFO

# GLOBAL SETTINGS
cwd = os.path.dirname(__file__)
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


@_contextmanager
def lvirtualenv(name):
    INPUT_PATH = os.path.join(cwd, name)
    with lcd(INPUT_PATH):
        with prefix('source venv/bin/activate'):
            yield


def zip_file(zipname, path, arcname=None, mode='w'):
    """
    Zip or append files
    - path: relative to fabfile.py
    - arcname: if different from path
    """
    OUTPUT_PATH = os.path.join(cwd, 'zip')
    INPUT_PATH = os.path.join(cwd, path)
    if not arcname:
        arcname = os.path.basename(INPUT_PATH)

    with zipfile.ZipFile('%s/%s.zip' % (OUTPUT_PATH, zipname), mode) as z:
        z.write(INPUT_PATH, arcname, zipfile.ZIP_DEFLATED)


def zip_contents(zipname, folder, excl_dirs, excl_ext, mode='w'):
    """
    Zip contents of folders recursively
    - folder: relative to fabfile.py
    - Ignoring folders names in excl_dirs
    - Ignoring file extensions in excl_ext
    """

    INPUT_PATH = os.path.join(cwd, folder)
    OUTPUT_PATH = os.path.join(cwd, 'zip')

    if not excl_ext:
        excl_ext = []
    if not excl_dirs:
        excl_dirs = []

    with zipfile.ZipFile('%s/%s.zip' % (OUTPUT_PATH, zipname), mode) as z:
        rootlen = len(INPUT_PATH) + 1
        for base, dirs, files in os.walk(INPUT_PATH):
            # Exclude folders in-place
            dirs[:] = [d for d in dirs if d not in excl_dirs]
            for file in files:
                if os.path.splitext(file)[1].lower() in excl_ext:
                    continue
                fn = os.path.join(base, file)
                logger.debug("arcname: %s" % fn[rootlen:])
                z.write(fn, fn[rootlen:], zipfile.ZIP_DEFLATED)


@task
def generateVirtualEnvironment(name):
    """
    Generate internal virtualenv so we can include dependencies
    """
    INPUT_PATH = os.path.join(cwd, name)
    with lcd(INPUT_PATH):
        command = 'virtualenv --no-site-packages venv'
        local(command)
    with lvirtualenv(name):
        local('pip install -r requirements.txt')


@task
def render(name):
    """
    Create lambda code deployment package
    - If the internal virtualenv has not been generated, do it!
    - Compress libraries
    - Add code files
    """
    # Sync the code from anno-docs
    execute(sync_anno_docs_files, 1)

    BASE_PATH = os.path.join(cwd, name)
    OUTPUT_PATH = os.path.join(cwd, 'zip')
    # Create output files folder if needed
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)
    # If we have requirements create internal virtualenv and zip
    if os.path.exists('%s/requirements.txt' % BASE_PATH):
        lib_path = os.path.join(cwd,
                                '%s/venv/lib/python2.7/site-packages' % (name))
        if not os.path.exists(lib_path):
            execute('generateVirtualEnvironment', name)
        try:
            # First zip all library dependencies
            zip_contents('code', 'code/venv/lib/python2.7/site-packages',
                         ['.git'], ['.pyc'], 'w')
            # Add source files
            zip_contents('code', 'code',
                         ['venv'], ['.pyc'], 'a')

            # Tweak aws shebang
            aws_path = 'code/venv/bin/aws'
            _tweak_aws_command(aws_path)
            # Add tweaked aws command line tool to zipfile
            zip_file('code', aws_path, None, 'a')
        except Exception, e:
            logger.error("Exit with uncaptured exception %s" % (e))
            raise

    else:
        # Add source files
        zip_contents('code', 'code', None, ['.pyc'], 'w')


@task
def deploy(name, function='anno-docs-lambda-stage'):
    execute('render', name)
    command = 'aws lambda update-function-code'
    command += ' --zip-file=fileb://zip/%s.zip' % (name)
    command += ' --function-name %s' % (function)
    logger.info('command: %s' % command)
    local(command)


@task
def sync_anno_docs_files(quiet=None):
    files = ['templates/_base.html',
             'templates/parent.html']
    src_root = 'https://raw.githubusercontent.com/nprapps/anno-docs/master'
    dst_root = 'code'
    for file in files:
        local('curl -s %s/%s -o %s/%s' % (
            src_root, file,
            dst_root, file))

    if not quiet:
        logger.info('Latest files downloaded. Now, git add & commit.')
        local('git status')


def _tweak_aws_command(path):
    """
    tweak aws command line tool to use system python in lambda environment
    via: https://alestic.com/2016/11/aws-lambda-awscli/
    """
    INPUT_PATH = os.path.join(cwd, path)
    with quiet():
        local('perl -pi -e \'$_ ="#!/usr/bin/python\n" if $. == 1\' %s' % (
              INPUT_PATH))
