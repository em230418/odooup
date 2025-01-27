import os

import click

from ._cache import cache_repo, parse_git_url
from ._helpers import call_cmd, mkdir_p
from .whitelist import enable_sparse_checkout_for_repo


def _clone(branch, url):
    repo_cache_dir = cache_repo(*parse_git_url(url))
    reference = "--reference {}".format(repo_cache_dir)
    target = get_fs_target(url)
    call_cmd(
        "git clone -b {branch} {reference} --dissociate "
        "{url} {target}".format(**locals()),
        echo_cmd=True,
        exit_on_error=True,
    )
    return target


def _clone_submodules(branch, target, dissociate):
    submodules = [
        s.split(" ")[1]
        for s in call_cmd(
            "git submodule", echo_cmd=False, exit_on_error=True, cwd=target
        ).split("\n")
    ]
    for submodule in submodules:
        name = call_cmd(
            "git submodule--helper name {}".format(submodule),
            echo_cmd=False,
            exit_on_error=True,
            cwd=target,
        )
        url = call_cmd(
            "git submodule--helper config submodule.{}.url".format(name),
            echo_cmd=False,
            exit_on_error=True,
            cwd=target,
        )
        if url.startswith(".") or url.startswith(".."):
            url = call_cmd(
                "git submodule--helper resolve-relative-url {}".format(url),
                echo_cmd=False,
                exit_on_error=True,
                cwd=target,
            )
        repo_cache_dir = cache_repo(*parse_git_url(url))
        reference = "--reference {}".format(repo_cache_dir)
        dissociate = "--dissociate" if dissociate else ""
        call_cmd(
            "git submodule update {reference} --init {dissociate} "
            "-- {submodule}".format(**locals()),
            echo_cmd=True,
            exit_on_error=False,
            cwd=target,
        )
    call_cmd(
        "git submodule foreach git config remote.origin.fetch "
        "+refs/heads/{branch}:refs/remotes/origin/{branch}".format(**locals()),
        echo_cmd=False,
        exit_on_error=True,
        cwd=target,
    )
    call_cmd(
        "git submodule foreach git fetch --all --prune",
        echo_cmd=False,
        exit_on_error=True,
        cwd=target,
    )


def clone_submodule_to_target(branch, url, target):
    repo_cache_dir = cache_repo(*parse_git_url(url))
    reference = "--reference {}".format(repo_cache_dir)
    call_cmd(
        "git submodule add -b {branch} {reference} --dissociate "
        "{url} {target}".format(**locals()),
        echo_cmd=True,
        exit_on_error=False,
    )


def get_fs_target(repo_url):
    _, _, org, project = parse_git_url(repo_url)
    home_path = os.path.expanduser("~")
    org_path = os.path.join(home_path, "odoo", org)
    mkdir_p(os.path.join(home_path, org_path))
    return os.path.join(home_path, org_path, project)


def get_vendor_target(repo_url):
    _, _, org, project = parse_git_url(repo_url)
    mkdir_p(os.path.join("vendor", org))
    return os.path.join("vendor", org, project)


@click.command()
@click.option(
    "--whitelist",
    is_flag=True,
    default=True,
    help="Initialize sparse checkout module whitelisting.",
)
@click.option(
    "--dissociate",
    is_flag=True,
    default=False,
    help="Dissociate cloned submodules from cache.",
)
@click.argument("branch", required=True)
@click.argument("url", required=True)
def clone(branch, url, whitelist, dissociate):
    target = _clone(branch, url)
    _clone_submodules(branch, target, dissociate)
    if whitelist:
        enable_sparse_checkout_for_repo(target)


if __name__ == "__main__":
    clone()
