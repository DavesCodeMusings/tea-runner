#!/usr/bin/env python3

"""
  Run tasks based on webhooks configured in Gitea.

  Command-line options:
    --debug, -d  Send more detailed log output to console.

  Configuration file (config.ini) options:

    [runner]
    ALLOWED_IP_RANGE=xxx.xxx.xxx.xxx/mm
    # Only respond to requests made from this range of IP addresses. Eg. 192.168.1.0/24
    LISTEN_IP=xxx.xxx.xxx.xxx
    # IP address for incoming requests. Defaults to 0.0.0.0 (Any).
    LISTEN_PORT=xxxx
    # TCP port number used for incoming requests. Defaults to 1706.

"""

GIT_BIN = '/usr/bin/git'
RSYNC_BIN = '/usr/bin/rsync'
DOCKER_BIN = '/usr/bin/docker'

import logging
from argparse import ArgumentParser
from configparser import ConfigParser
from flask import Flask, request, jsonify
from werkzeug import utils
from waitress import serve
from tempfile import TemporaryDirectory
from os import access, X_OK, chdir, path
from sys import exit
from subprocess import run, DEVNULL
from os import path
from ipaddress import ip_address, ip_network

print("Tea Runner")

# Debug is a command-line option, but most configuration comes from config.ini
arg_parser = ArgumentParser()
arg_parser.add_argument('-d', '--debug', action='store_true', help='display debugging output while running')
args = arg_parser.parse_args()

if args.debug:
  logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
else:
  logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

config = ConfigParser()
config.read('config.ini')


if not access(GIT_BIN, X_OK):
  logging.error("git binary not found or not executable")
  exit(1)
if not access(RSYNC_BIN, X_OK):
  logging.error("rsync binary not found or not executable")
  exit(1)
if not access(DOCKER_BIN, X_OK):
  logging.error("docker binary not found or not executable")
  exit(1)


def git_clone(src_url, dest_dir):
  """
    Clone a remote git repository into a local directory.
      :src_url (string): HTTP(S) url used to clone the repo.
      :dest_dir (string): Path to the local directory.
      :returns (boolean): True if command returns success.
  """

  logging.info('git clone ' + src_url)
  chdir(dest_dir)
  clone_result = run([GIT_BIN, 'clone', src_url, '.'],
    stdout=None if args.debug else DEVNULL, stderr=None if args.debug else DEVNULL)
  return clone_result.returncode == 0


app = Flask(__name__)

@app.before_request
def check_authorized():
  """
    Only respond to requests from ALLOWED_IP_RANGE if it's configured in config.ini
  """

  if config.has_option('runner', 'ALLOWED_IP_RANGE'):
    allowed_ip_range = ip_network(config['runner']['ALLOWED_IP_RANGE'])
    requesting_ip = ip_address(request.remote_addr)
    if requesting_ip not in allowed_ip_range:
      logging.info('Dropping request from unauthorized host ' + request.remote_addr)
      return jsonify(status='forbidden'), 403
    else:
      logging.info('Request from ' + request.remote_addr)


@app.before_request
def check_media_type():
  """
    Only respond requests with Content-Type header of application/json
  """
  if not request.headers.get('Content-Type').lower().startswith('application/json'):
    logging.error('"Content-Type: application/json" header missing from request made by ' + request.remote_addr)
    return jsonify(status='unsupported media type'), 415


@app.route('/test', methods=['POST'])
def test():
  logging.debug('Content-Type: ' + request.headers.get('Content-Type'))
  logging.debug(request.get_json(force=True))
  return jsonify(status='success', sender=request.remote_addr)


@app.route('/rsync', methods=['POST'])
def rsync():
  body = request.get_json()
  dest = request.args.get('dest') or body['repository']['name']
  rsync_root = config.get('rsync', 'RSYNC_ROOT', fallback='')
  if rsync_root:
    dest = path.join(rsync_root, utils.secure_filename(dest))
    logging.debug('rsync dest path updated to ' + dest)

  with TemporaryDirectory() as temp_dir:
    if git_clone(body['repository']['clone_url'], temp_dir):
      logging.info('rsync ' + body['repository']['name'] + ' to ' + dest)
      chdir(temp_dir)
      result = run([RSYNC_BIN, '-r', '--exclude=.git', '.', dest],
        stdout=None if args.debug else DEVNULL, stderr=None if args.debug else DEVNULL)
      if result.returncode != 0:
        return jsonify(status='rsync failed'), 500
    else:
      return jsonify(status='git clone failed'), 500

  return jsonify(status='success')


@app.route('/docker/build', methods=['POST'])
def docker_build():
  body = request.get_json()

  with TemporaryDirectory() as temp_dir:
    if git_clone(body['repository']['clone_url'], temp_dir):
      logging.info('docker build')
      chdir(temp_dir)
      result = run([DOCKER_BIN, 'build', '-t', body['repository']['name'], '.'],
        stdout=None if args.debug else DEVNULL, stderr=None if args.debug else DEVNULL)
      if result.returncode != 0:
        return jsonify(status='docker build failed'), 500
    else:
      return jsonify(status='git clone failed'), 500

  return jsonify(status='success')


if __name__ == '__main__':
  logging.info('Limiting requests to: ' + config.get('runner', 'ALLOWED_IP_RANGE', fallback='<any>'))
  serve(app, host=config.get('runner', 'LISTEN_IP', fallback='0.0.0.0'),
    port=config.getint('runner', 'LISTEN_PORT', fallback=1706))
