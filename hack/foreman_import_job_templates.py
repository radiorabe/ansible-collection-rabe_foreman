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
from textwrap import dedent

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

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


def LS(string):  # noqa: N802
    """
    Make Literal Scalar string.

    Args:
        string: string

    Returns:
        literal scalar string
    """
    return LiteralScalarString(dedent(string))


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


def strip_leading_double_space(stream):
    """
    Strip leading two spaces for yaml output.

    https://stackoverflow.com/a/58773229

    Args:
        stream: ie. stdout

    Returns:
        stream
    """
    if stream.startswith("  "):
        stream = stream[2:]
    return stream.replace("\n  ", "\n")


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
        # more bespoke templates get added here
        {
            _FIELD_NAME: "Ansible Collection - Upgrade from Galaxy",
            _FIELD_STATE: _STATE_PRESENT,
            "job_category": "Ansible Galaxy",
            "description_format": "Upgrade collections '%{ansible_collections_list}' from Galaxy",  # noqa: E501
            "snippet": False,
            "template_inputs": [
                {
                    "name": "ansible_collections_list",
                    "required": True,
                    "input_type": "user",
                    "description": LS("List of collections in Ansible Galaxy to install, separated by commas, e.g: mysql,nginx\nThe default collections_paths is configured in /etc/ansible/ansible.cfg, you may override it by filling the 'collections_path' input. Click on \"Advanced\" to see it."),  # noqa: E501
                    "advanced": False,
                },
                {
                    "name": "collections_path",
                    "required": False,
                    "input_type": "user",
                    "description": LS("A particular directory where you want the downloaded collections to be placed."),  # noqa: E501
                    "advanced": True,
                },
            ],
            "provider_type": "Ansible",
            "kind": "job_template",
            "model": "JobTemplate",
            "file_name": "{{ role_path }}/../../../rabe_foreman/roles/foreman/files/job_templates/ansible_collections_-_install_from_galaxy.erb",  # noqa: E501
        },
        {
            _FIELD_NAME: "RaBe Foreman - Publish Content View",
            _FIELD_STATE: _STATE_PRESENT,
            "job_category": "RaBe Foreman",
            "description_format": "RaBe Foreman - Publish Content View",
            "snippet": False,
            "provider_type": "Ansible",
            "kind": "job_template",
            "model": "JobTemplate",
            "file_name": "{{ role_path }}/../../../rabe_foreman/roles/foreman/files/job_templates/rabe_foreman_publish_content_view.erb",  # noqa: E501
        },
        {
            _FIELD_NAME: "RaBe Foreman - Promote Content Views to Prod",
            _FIELD_STATE: _STATE_PRESENT,
            "job_category": "RaBe Foreman",
            "description_format": "RaBe Foreman - Promote Content Views to Prod",  # noqa: E501
            "snippet": False,
            "template_inputs": [
                {
                    "name": "lifecycle_environment",
                    "required": True,
                    "input_type": "user",
                    "description": LS("Target Environment."),  # noqa: E501
                    "advanced": True,
                    "default": "Prod"
                },
            ],
            "provider_type": "Ansible",
            "kind": "job_template",
            "model": "JobTemplate",
            "file_name": "{{ role_path }}/../../../rabe_foreman/roles/foreman/files/job_templates/rabe_foreman_promote_content_views.erb",  # noqa: E501
        },
    ]  # noqa: T801
    final_data = [
        {
            _FIELD_NAME: "RaBe Foreman Config : Job Templates",
            "block": [
                {
                    _FIELD_NAME: "RaBe Foreman Config : Unlock All Job Templates",  # noqa: E501
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
                    _FIELD_NAME: "RaBe Foreman Config : Configure Job Templates",  # noqa: E501
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
                    _FIELD_NAME: "RaBe Foreman Config : Lock All Job Templates",  # noqa: E501
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
    yml = YAML()
    yml.explicit_start = True
    yml.indent(mapping=2, sequence=4, offset=2)
    yml.dump(final_data, stdout, transform=strip_leading_double_space)


if __name__ == "__main__":
    main(REPOS)
