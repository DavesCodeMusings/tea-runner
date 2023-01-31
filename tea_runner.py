#!/usr/bin/env python3

"""
Run tasks based on webhooks configured in Gitea.

Command-line options:
    --debug, -d  Send more detailed log output to console.

Configuration file (config.ini) options:

    [runner]
    ALLOWED_IP_RANGE=xxx.xxx.xxx.xxx/mm
    # Only respond to requests made from this range of IP addresses. Eg. 192.168.1.0/24
    GIT_PROTOCOL=<http|ssh>
    # Choose the protocol to use when cloning repositories. Default to http
    GIT_SSL_NO_VERIFY=true
    # Ignore certificate host verification errors. Useful for self-signed certs.
    GIT_SSH_NO_VERIFY=true
    # Ignore certificate host verification errors.
    LISTEN_IP=xxx.xxx.xxx.xxx
    # IP address for incoming requests. Defaults to 0.0.0.0 (Any).
    LISTEN_PORT=xxxx
    # TCP port number used for incoming requests. Defaults to 1706.
"""

import asyncio
from argparse import ArgumentParser
from configparser import ConfigParser

from hypercorn.asyncio import Config, serve

import runner

# Debug is a command-line option, but most configuration comes from config.ini
arg_parser = ArgumentParser()
arg_parser.add_argument(
    "-d", "--debug", action="store_true", help="display debugging output while running"
)
args = arg_parser.parse_args()

quart_config = ConfigParser()
quart_config.read("config.ini")
hypercorn_config = Config()

hypercorn_config.bind = (
    quart_config.get("runner", "LISTEN_IP", fallback="0.0.0.0")
    + ":"
    + str(quart_config.getint("runner", "LISTEN_PORT", fallback=1706))
)

if args.debug:
    quart_config.set("runner", "DEBUG", "true")
    hypercorn_config.loglevel = "debug"

asyncio.run(serve(runner.create_app(quart_config), hypercorn_config))
