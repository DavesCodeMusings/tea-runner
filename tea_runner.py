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

import logging
from argparse import ArgumentParser
from configparser import ConfigParser
from ipaddress import ip_address, ip_network
from os import access, environ, X_OK
from shutil import which
from sys import exit

from quart import Quart, request, jsonify

import runner.utils

print("Tea Runner")

# Debug is a command-line option, but most configuration comes from config.ini
arg_parser = ArgumentParser()
arg_parser.add_argument(
    "-d", "--debug", action="store_true", help="display debugging output while running"
)
args = arg_parser.parse_args()


app = Quart(__name__)


@app.before_request
async def check_authorized():
    """
    Only respond to requests from ALLOWED_IP_RANGE if it's configured in config.ini
    """
    if app.runner_config.has_option("runner", "ALLOWED_IP_RANGE"):
        allowed_ip_range = ip_network(app.runner_config["runner"]["ALLOWED_IP_RANGE"])
        requesting_ip = ip_address(request.remote_addr)
        if requesting_ip not in allowed_ip_range:
            logging.info(
                "Dropping request from unauthorized host " + request.remote_addr
            )
            return jsonify(status="forbidden"), 403
        else:
            logging.info("Request from " + request.remote_addr)


@app.before_request
async def check_media_type():
    """
    Only respond requests with Content-Type header of application/json
    """
    if not request.headers.get("Content-Type").lower().startswith("application/json"):
        logging.error(
            '"Content-Type: application/json" header missing from request made by '
            + request.remote_addr
        )
        return jsonify(status="unsupported media type"), 415


@app.route("/test", methods=["POST"])
async def test():
    logging.debug("Content-Type: " + request.headers.get("Content-Type"))
    logging.debug(await request.get_json(force=True))
    return jsonify(status="success", sender=request.remote_addr)


if __name__ == "__main__":
    app.runner_config = ConfigParser()
    app.runner_config.read("config.ini")

    if args.debug:
        app.runner_config.set("runner", "DEBUG", "true")

    if app.runner_config.getboolean("runner", "DEBUG", fallback="False") == True:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)
        logging.info("Debug logging is on")
    else:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    app.git_protocol = app.runner_config.get("runner", "GIT_PROTOCOL", fallback="http")
    logging.info("git protocol is " + app.git_protocol)

    logging.info(
        "Limiting requests to: "
        + app.runner_config.get("runner", "ALLOWED_IP_RANGE", fallback="<any>")
    )

    app.git = which("git")
    app.rsync = which("rsync")
    app.docker = which("docker")
    app.tf_bin = which("terraform")

    try:
        access(app.git, X_OK)
    except:
        logging.error("git binary not found or not executable")
        exit(1)
    try:
        access(app.rsync, X_OK)
    except:
        logging.error("rsync binary not found or not executable")
        exit(1)
    try:
        access(app.docker, X_OK)
    except:
        logging.error("docker binary not found or not executable")
        exit(1)
    try:
        access(app.tf_bin, X_OK)
    except:
        logging.error("terraform binary not found or not executable")
        exit(1)

    if (
        app.runner_config.getboolean("runner", "GIT_SSL_NO_VERIFY", fallback="False")
        == True
    ):
        environ["GIT_SSL_NO_VERIFY"] = "true"
    if (
        app.runner_config.getboolean("runner", "GIT_SSH_NO_VERIFY", fallback="False")
        == True
    ):
        environ[
            "GIT_SSH_COMMAND"
        ] = "ssh -o UserKnownHostsFile=test -o StrictHostKeyChecking=no"

    from runner.docker import docker as docker_bp
    from runner.rsync import rsync as rsync_bp
    from runner.terraform import terraform as terraform_bp

    app.register_blueprint(docker_bp, url_prefix="/docker")
    app.register_blueprint(rsync_bp)
    app.register_blueprint(terraform_bp, url_prefix="/terraform")


    app.run(
        host=app.runner_config.get("runner", "LISTEN_IP", fallback="0.0.0.0"),
        port=app.runner_config.getint("runner", "LISTEN_PORT", fallback=1706),
        debug=logging.root.level,
    )
