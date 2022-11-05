"""
Create tasks/job_templates.yaml to manage 'Hosts' > 'Templates' > 'Job Templates'.

Usage:
    python ./hack/foreman_import_job_templates.py \
            > roles/foreman/tasks/job_templates.yaml

They unlock all the templates during operation and re-lock them all when it's
done. This isn't idempotent which is fine for now. At some point we'll want to
refactor it to check if any changes are needed before unlocking and relocking
all the tempaltes.

Most scripts in here were originally exported from foreman and are here to
document which one of them we keep and which we update. We expect to add some
RaBe specific scripts once the default set is tweaked. As a rule of thumb, we
deactivate built-in templates and replace them with copies of our own were
possible.

The canonical sources for the templates we don't maintain ourselves are in
various difference repos:

- [Foreman Ansible Jobs](https://github.com/theforeman/foreman_ansible/tree/master/app/views/foreman_ansible/job_templates)
- [Katello Jobs](https://github.com/Katello/katello/tree/master/app/views/foreman/job_templates)
- [OpenSCAP](https://github.com/theforeman/foreman_openscap/tree/master/app/views/job_templates)

Please add more links as you find them.
"""  # noqa: E501

from itertools import chain
from os import environ, listdir
from os.path import basename, isfile, join
from pathlib import Path
from re import DOTALL, search
from sys import stdout

import yaml

HOME = environ["HOME"]
BASE = f"{HOME}/Documents/git.repos"
REPOS = (
    f"{BASE}/theforeman/foreman_ansible/app/views/foreman_ansible/job_templates",  # noqa: E501
    f"{BASE}/Katello/katello/app/views/foreman/job_templates",
    f"{BASE}/theforeman/foreman_openscap/app/views/job_templates",
)
TARGET = f"{BASE}/rabe/ansible-collection-rabe_foreman/roles/foreman/files/job_templates"  # noqa: E501
_ABSENTEES = ("ansible_windows_updates.erb",)


_FIELD_NAME = "name"
_FIELD_STATE = "state"
_STATE_ABSENT = "absent"
_STATE_PRESENT = "present"


def scan_dir(template_dir):
    """
    Get all files in a dir.

    Args:
        template_dir: dir to scan

    Returns:
        a list of paths
    """
    return [
        join(template_dir, filename)
        for filename in listdir(template_dir)
        if isfile(join(template_dir, filename))
    ]  # noqa: WPS221


def files(template_dirs):
    """
    Get all template files to import.

    Args:
        template_dirs: list of dirs to scan.

    Returns:
        list of found templates
    """
    return list(chain(*[scan_dir(repo) for repo in template_dirs]))


def read_file(tpl_file):
    """
    Read file and split it into parts.

    Args:
        tpl_file: file to load

    Returns:
        A tuple with (tpl_file, basename, meta, code) as contents.

    Raises:
        RuntimeError: if it can't read a template.
    """
    raw = open(tpl_file, "r").read()  # noqa: WPS515
    header = search("<%#(.+?)\n(-*)%>\n(.*)", raw, DOTALL)
    if header is None:
        raise RuntimeError("No header found in template")
    meta = yaml.safe_load(header.group(1))
    code = header.group(3)
    file_basename = basename(tpl_file)
    return (tpl_file, file_basename, meta, code)


def write_file(file_info):
    """
    Put file in proper directory.

    Args:
        file_info: tuple with info about file
    """
    (_, file_basename, _, code) = file_info
    target_filename = join(TARGET, file_basename)
    Path(target_filename).write_text(code)


def gen_data(file_info):
    """
    Generate a block of ansible per file.

    Args:
        file_info: list of file info tuples

    Returns:
        data structure for ansible
    """
    (_, file_basename, meta, _) = file_info
    meta[_FIELD_STATE] = _STATE_PRESENT
    if file_basename in _ABSENTEES:
        meta[_FIELD_STATE] = _STATE_ABSENT
    meta["file_name"] = join(
        "{{ role_path }}/../../../rabe_foreman",
        "roles/foreman/files/job_templates",
        file_basename,
    )

    return meta


def main(template_paths: list[str]):
    """
    Generate new job_templates.yaml on stdout and put files into dir.

    Args:
        template_paths: int | float, the divisor in the division

    :return: void
    """
    tpl_data = [read_file(tpl_file) for tpl_file in files(template_paths)]
    [write_file(file_info) for file_info in tpl_data]  # noqa: WPS428
    defaults = [
        # cloud connector was originally in ansible_foreman but moved to
        # foreman_rh_cloud at some point:
        # - https://github.com/theforeman/foreman_ansible/pull/526
        {
            _FIELD_NAME: "Configure Cloud Connector",
            _FIELD_STATE: _STATE_ABSENT,
        },
        {
            _FIELD_NAME: "Convert to RHEL",
            _FIELD_STATE: _STATE_ABSENT,
        },
        # This sync script currently doesn't care about copying and managing
        # puppet stuff like the rest that can get deactivated via ABSENTEES
        {
            _FIELD_NAME: "Puppet Agent Disable - Script Default",
            _FIELD_STATE: _STATE_ABSENT,
        },
        {
            _FIELD_NAME: "Puppet Agent Enable - Script Default",
            _FIELD_STATE: _STATE_ABSENT,
        },
        {
            _FIELD_NAME: "Puppet Module - Install from forge - Script Default",
            _FIELD_STATE: _STATE_ABSENT,
        },
        {
            _FIELD_NAME: "Puppet Module - Install from git - Script Default",
            _FIELD_STATE: _STATE_ABSENT,
        },
        {
            _FIELD_NAME: "Puppet Run Once - Ansible Default",
            _FIELD_STATE: _STATE_ABSENT,
        },
        {
            _FIELD_NAME: "Puppet Run Once - Script Default",
            _FIELD_STATE: _STATE_ABSENT,
        },
    ]  # noqa: T801
    final_data = [
        {
            _FIELD_NAME: "radiorabe.rabe_foreman.foreman : Job Templates",
            "block": [
                {
                    _FIELD_NAME: "radiorabe.rabe_foreman.foreman : Unlock All Job Templates",  # noqa: E501
                    "ansible.builtin.include_role": {
                        _FIELD_NAME: "radiorabe.foreman.job_templates",
                    },
                    "vars": {
                        "foreman_job_templates": [
                            {
                                _FIELD_NAME: "*",
                                "locked": False,
                            },
                        ],
                    },
                    "when": "not ansible_check_mode",
                },
                {
                    _FIELD_NAME: "radiorabe.rabe_foreman.foreman : Configure Job Templates",  # noqa: E501
                    "ansible.builtin.include_role": {
                        _FIELD_NAME: "radiorabe.foreman.job_templates",
                    },
                    "vars": {
                        "foreman_job_templates": [
                            gen_data(tpl_file) for tpl_file in tpl_data
                        ]
                        + defaults,  # noqa: E501
                    },
                    "when": "not ansible_check_mode",
                },
            ],
            "always": [
                {
                    _FIELD_NAME: "radiorabe.rabe_foreman.foreman : Lock All Job Templates",  # noqa: E501
                    "ansible.builtin.include_role": {
                        _FIELD_NAME: "radiorabe.foreman.job_templates",
                    },
                    "vars": {
                        "foreman_job_templates": [
                            {
                                _FIELD_NAME: "*",
                                "locked": True,
                            },
                        ],
                    },
                    "when": "not ansible_check_mode",
                },
            ],
        },
    ]
    stdout.write("---\n")
    stdout.write(yaml.safe_dump(final_data))


if __name__ == "__main__":
    main(REPOS)
