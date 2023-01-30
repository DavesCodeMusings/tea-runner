import logging
from os import chdir, path
from subprocess import run, DEVNULL
from tempfile import TemporaryDirectory

from flask import Blueprint, current_app, jsonify, request
from werkzeug import utils

import runner.utils

rsync = Blueprint("rsync", __name__)


@rsync.route("/rsync", methods=["POST"])
def route_rsync():
    body = request.get_json()
    dest = request.args.get("dest") or body["repository"]["name"]
    rsync_root = current_app.runner_config.get("rsync", "RSYNC_ROOT", fallback="")
    if rsync_root:
        dest = path.join(rsync_root, utils.secure_filename(dest))
        logging.debug("rsync dest path updated to " + dest)

    with TemporaryDirectory() as temp_dir:
        if runner.utils.git_clone(
            body["repository"]["clone_url"]
            if current_app.git_protocol == "http"
            else body["repository"]["ssh_url"],
            temp_dir,
        ):
            logging.info("rsync " + body["repository"]["name"] + " to " + dest)
            chdir(temp_dir)
            if current_app.runner_config.get("rsync", "DELETE", fallback=""):
                result = run(
                    [
                        current_app.rsync,
                        "-r",
                        "--exclude=.git",
                        "--delete-during"
                        if current_app.runner_config.get("rsync", "DELETE", fallback="")
                        else "",
                        ".",
                        dest,
                    ],
                    stdout=None if logging.root.level == logging.DEBUG else DEVNULL,
                    stderr=None if logging.root.level == logging.DEBUG else DEVNULL,
                )
            else:
                result = run(
                    [current_app.rsync, "-r", "--exclude=.git", ".", dest],
                    stdout=None if logging.root.level == logging.DEBUG else DEVNULL,
                    stderr=None if logging.root.level == logging.DEBUG else DEVNULL,
                )
            if result.returncode != 0:
                return jsonify(status="rsync failed"), 500
        else:
            return jsonify(status="git clone failed"), 500

    return jsonify(status="success")
