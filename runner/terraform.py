import logging
from os import chdir
from subprocess import run, DEVNULL
from tempfile import TemporaryDirectory

from quart import Blueprint, current_app, jsonify, request

import runner.utils

terraform = Blueprint("terraform", __name__)


@terraform.route("/plan", methods=["POST"])
async def terraform_plan():
    body = await request.get_json()

    with TemporaryDirectory() as temp_dir:
        if runner.utils.git_clone(
            body["repository"]["clone_url"]
            if current_app.git_protocol == "http"
            else body["repository"]["ssh_url"],
            temp_dir,
        ):
            logging.info("terraform init")
            chdir(temp_dir)
            result = run(
                [current_app.tf_bin, "init", "-no-color"],
                stdout=None if logging.root.level == logging.DEBUG else DEVNULL,
                stderr=None if logging.root.level == logging.DEBUG else DEVNULL,
            )
            if result.returncode != 0:
                return jsonify(status="terraform init failed"), 500
            result = run(
                [current_app.tf_bin, "plan", "-no-color"], stdout=None, stderr=None
            )
            if result.returncode != 0:
                return jsonify(status="terraform plan failed"), 500
        else:
            return jsonify(status="git clone failed"), 500

    return jsonify(status="success")


@terraform.route("/apply", methods=["POST"])
def terraform_apply():
    body = request.get_json()
    with TemporaryDirectory() as temp_dir:
        if runner.utils.git_clone(
            body["repository"]["clone_url"]
            if current_app.git_protocol == "http"
            else body["repository"]["ssh_url"],
            temp_dir,
        ):
            logging.info("terraform init")
            chdir(temp_dir)
            result = run(
                [current_app.tf_bin, "init", "-no-color"],
                stdout=None if logging.root.level == logging.DEBUG else DEVNULL,
                stderr=None if logging.root.level == logging.DEBUG else DEVNULL,
            )
            if result.returncode != 0:
                return jsonify(status="terraform init failed"), 500
            result = run(
                [current_app.tf_bin, "apply", "-auto-approve", "-no-color"],
                stdout=None if logging.root.level == logging.DEBUG else DEVNULL,
                stderr=None if logging.root.level == logging.DEBUG else DEVNULL,
            )
            if result.returncode != 0:
                return jsonify(status="terraform apply failed"), 500
        else:
            return jsonify(status="git clone failed"), 500

    return jsonify(status="success")
