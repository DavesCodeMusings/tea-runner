import logging
from ipaddress import ip_address, ip_network
from os import access, environ, X_OK
from shutil import which

from quart import Quart, request, jsonify


def create_app(config):
    print("Tea Runner")
    # Configure loglevel
    if config.getboolean("runner", "DEBUG", fallback="False") == True:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)
        logging.info("Debug logging is on")
    else:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    app = Quart(__name__)

    # Configure Quart
    app.runner_config = config
    app.git_protocol = app.runner_config.get("runner", "GIT_PROTOCOL", fallback="http")

    # Check presence of external programs
    app.docker = which("docker")
    try:
        access(app.docker, X_OK)
    except:
        logging.error("docker binary not found or not executable")
        exit(1)

    app.git = which("git")
    try:
        access(app.git, X_OK)
    except:
        logging.error("git binary not found or not executable")
        exit(1)

    app.rsync = which("rsync")
    try:
        access(app.rsync, X_OK)
    except:
        logging.error("rsync binary not found or not executable")
        exit(1)

    app.tf_bin = which("terraform")
    try:
        access(app.tf_bin, X_OK)
    except:
        logging.error("terraform binary not found or not executable")
        exit(1)

    # Set environment variables
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

    # Log some informations
    logging.info("git protocol is " + app.git_protocol)
    logging.info(
        "Limiting requests to: "
        + app.runner_config.get("runner", "ALLOWED_IP_RANGE", fallback="<any>")
    )

    @app.before_request
    async def check_authorized():
        """
        Only respond to requests from ALLOWED_IP_RANGE if it's configured in config.ini
        """
        if app.runner_config.has_option("runner", "ALLOWED_IP_RANGE"):
            allowed_ip_range = ip_network(
                app.runner_config["runner"]["ALLOWED_IP_RANGE"]
            )
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
        if (
            not request.headers.get("Content-Type")
            .lower()
            .startswith("application/json")
        ):
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

    # Register Blueprints
    from runner.docker import docker as docker_bp
    from runner.rsync import rsync as rsync_bp
    from runner.terraform import terraform as terraform_bp

    app.register_blueprint(docker_bp, url_prefix="/docker")
    app.register_blueprint(rsync_bp)
    app.register_blueprint(terraform_bp, url_prefix="/terraform")

    return app
