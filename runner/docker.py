import logging
from os import chdir, path
from subprocess import run, DEVNULL
from tempfile import TemporaryDirectory

from flask import Blueprint, current_app, jsonify, request

import runner.utils

docker = Blueprint("docker", __name__)


@docker.route("/build", methods=["POST"])
def docker_build():
    body = request.get_json()

    with TemporaryDirectory() as temp_dir:
        if runner.utils.git_clone(
            body["repository"]["clone_url"]
            if current_app.git_protocol == "http"
            else body["repository"]["ssh_url"],
            temp_dir,
        ):
            logging.info("docker build")
            chdir(temp_dir)
            result = run(
                [current_app.docker, "build", "-t", body["repository"]["name"], "."],
                stdout=None if logging.root.level == logging.DEBUG else DEVNULL,
                stderr=None if logging.root.level == logging.DEBUG else DEVNULL,
            )
            if result.returncode != 0:
                return jsonify(status="docker build failed"), 500
        else:
            return jsonify(status="git clone failed"), 500

    return jsonify(status="success")
