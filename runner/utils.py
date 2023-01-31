import logging
from os import chdir
from subprocess import run, DEVNULL

from quart import current_app


def git_clone(src_url, dest_dir):
    """
    Clone a remote git repository into a local directory.

    Args:
        src_url (string): Url used to clone the repo.
        dest_dir (string): Path to the local directory.

    Returns:
       (boolean): True if command returns success.
    """

    logging.info("git clone " + src_url)
    chdir(dest_dir)
    clone_result = run(
        [current_app.git, "clone", src_url, "."],
        stdout=None if logging.root.level == logging.DEBUG else DEVNULL,
        stderr=None if logging.root.level == logging.DEBUG else DEVNULL,
    )
    return clone_result.returncode == 0
