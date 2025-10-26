#!/usr/bin/python

from __future__ import annotations

import json
import os
import re
import subprocess
from io import StringIO

from ansible.module_utils.basic import AnsibleModule
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import (
    DoubleQuotedScalarString,
    LiteralScalarString,
)


def _yaml_loader():
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.explicit_start = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def _to_plain(value):
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    return value


def _to_yaml_node(value):
    if isinstance(value, dict):
        out = CommentedMap()
        for key, val in value.items():
            out[key] = _to_yaml_node(val)
        return out
    if isinstance(value, list):
        out = CommentedSeq()
        for item in value:
            out.append(_to_yaml_node(item))
        return out
    if isinstance(value, str):
        if "\n" in value:
            return LiteralScalarString(value)
        if "{{" in value or "{%" in value:
            return DoubleQuotedScalarString(value)
    return value


def _deep_merge(base, updates):
    if not isinstance(base, dict):
        base = {}
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _json_equal(a, b):
    return json.dumps(_to_plain(a), sort_keys=True) == json.dumps(
        _to_plain(b), sort_keys=True
    )


def _plain_equal(a, b):
    return _json_equal(_to_plain(a), _to_plain(b))


def _load_existing_content(repo_root, output_path):
    rel_path = None
    abs_repo = os.path.abspath(repo_root)
    abs_output = os.path.abspath(output_path)
    if abs_output.startswith(abs_repo + os.sep):
        rel_path = os.path.relpath(abs_output, abs_repo)

    if rel_path:
        proc = subprocess.run(
            [
                "git",
                "-C",
                abs_repo,
                "--no-pager",
                "show",
                f"HEAD:{rel_path}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return proc.stdout

    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            return f.read()

    return ""


def _normalize_doc_start(content):
    if not content.strip():
        return "---\n"

    if content.startswith("---"):
        return re.sub(r"\A(?:---\s*\n)+", "---\n", content, count=1)

    return "---\n" + content.lstrip()


def _normalize_params(existing_params, source_params):
    normalized = []
    seen = []

    source_by_name = {
        p.get("name"): p for p in source_params if isinstance(p, dict) and p.get("name")
    }

    # Preserve ordering from existing file for params
    # that still exist in Foreman.
    for existing in existing_params:
        if not isinstance(existing, dict):
            continue
        name = existing.get("name")
        if not name or name not in source_by_name:
            continue

        source = source_by_name[name]
        source_hidden = bool(
            source.get("hidden_value?", source.get("hidden_value", False))
        )
        item = {
            "name": name,
            "parameter_type": source.get("parameter_type", "string"),
            "value": source.get("value"),
        }
        if source_hidden:
            item["hidden_value"] = True
        normalized.append(item)
        seen.append(name)

    # Append newly discovered Foreman params after existing-ordered ones.
    for source in source_params:
        if not isinstance(source, dict):
            continue
        name = source.get("name")
        if not name or name in seen:
            continue

        source_hidden = bool(
            source.get("hidden_value?", source.get("hidden_value", False))
        )
        item = {
            "name": name,
            "parameter_type": source.get("parameter_type", "string"),
            "value": source.get("value"),
        }
        if source_hidden:
            item["hidden_value"] = True
        normalized.append(item)

    return normalized


def _merge_parameter_seq(existing_seq, new_params):
    if not isinstance(existing_seq, CommentedSeq):
        return _to_yaml_node(new_params)

    existing_by_name = {}
    for item in existing_seq:
        if isinstance(item, CommentedMap):
            name = item.get("name")
            if name:
                existing_by_name[name] = item

    merged_seq = CommentedSeq()
    for param in new_params:
        name = param.get("name") if isinstance(param, dict) else None
        existing_item = existing_by_name.get(name)

        if isinstance(existing_item, CommentedMap):
            # Remove keys no longer present in Foreman data.
            for key in list(existing_item.keys()):
                if key not in param:
                    del existing_item[key]

            # Update values while retaining comments attached
            # to existing nodes.
            for key, value in param.items():
                if key in existing_item and _plain_equal(existing_item[key], value):
                    continue
                existing_item[key] = _to_yaml_node(value)

            # Keep predictable key order inside each parameter item.
            for key in param.keys():
                if key in existing_item:
                    existing_item.move_to_end(key)

            merged_seq.append(existing_item)
        else:
            merged_seq.append(_to_yaml_node(param))

    return merged_seq


def run_module():
    module = AnsibleModule(
        argument_spec={
            "repo_root": {"type": "path", "required": True},
            "output_path": {"type": "path", "required": True},
            "hostgroup": {"type": "dict", "required": True},
            "role_entries": {
                "type": "list",
                "elements": "dict",
                "required": False,
                "default": [],
            },
        },
        supports_check_mode=True,
    )

    repo_root = module.params["repo_root"]
    output_path = module.params["output_path"]
    hostgroup = module.params["hostgroup"] or {}
    role_entries = module.params["role_entries"] or []

    existing_content = _load_existing_content(repo_root, output_path)
    existing_trimmed = existing_content.strip()

    yaml = _yaml_loader()
    existing_data = yaml.load(existing_trimmed) if existing_trimmed else CommentedMap()
    if existing_data is None:
        existing_data = CommentedMap()

    existing_hostgroup_rt = existing_data.get("foreman_hostgroup", CommentedMap())
    existing_hostgroup = _to_plain(
        existing_hostgroup_rt if isinstance(existing_hostgroup_rt, dict) else {}
    )

    source_params = hostgroup.get("parameters") or []
    existing_params = existing_hostgroup.get("parameters") or []
    merged_params = _normalize_params(existing_params, source_params)

    fetched_roles = [
        r.get("name")
        for r in role_entries
        if isinstance(r, dict) and not r.get("inherited", False) and r.get("name")
    ]
    roles_value = fetched_roles if fetched_roles else None

    merged_architecture = hostgroup.get("architecture_name")
    dumped_architecture = (
        None if merged_architecture == "x86_64" else merged_architecture
    )

    orgs = hostgroup.get("organizations") or []
    locs = hostgroup.get("locations") or []

    updates = {
        "name": hostgroup.get("name"),
        "description": hostgroup.get("description"),
        "parent": hostgroup.get("parent_name"),
        "organization": (
            orgs[0].get("name") if len(orgs) > 0 and isinstance(orgs[0], dict) else None
        ),
        "locations": (
            [
                loc.get("name")
                for loc in locs
                if isinstance(loc, dict) and loc.get("name")
            ]
            if len(locs) > 0
            else None
        ),
        "domain": hostgroup.get("domain_name"),
        "subnet": hostgroup.get("subnet_name"),
        "architecture": dumped_architecture,
        "operatingsystem": hostgroup.get("operatingsystem_name"),
        "lifecycle_environment": hostgroup.get("lifecycle_environment_name"),
        "content_view": hostgroup.get("content_view_name"),
        "compute_resource": hostgroup.get("compute_resource_name"),
        "compute_profile": hostgroup.get("compute_profile_name"),
        "ansible_roles": roles_value,
        "parameters": merged_params if merged_params else None,
    }

    merged_hostgroup = updates

    ordered_keys = list(existing_hostgroup.keys())
    for key in updates.keys():
        if key not in ordered_keys:
            ordered_keys.append(key)

    merged_ordered = CommentedMap()
    for key in ordered_keys:
        if key in merged_hostgroup and merged_hostgroup.get(key) is not None:
            merged_ordered[key] = merged_hostgroup.get(key)

    if existing_hostgroup and _json_equal(
        _to_plain(merged_ordered), existing_hostgroup
    ):
        rendered = _normalize_doc_start(existing_content)
    else:
        out_data = existing_data if isinstance(existing_data, dict) else CommentedMap()
        fg = out_data.get("foreman_hostgroup")
        if not isinstance(fg, CommentedMap):
            fg = CommentedMap()

        for key in list(fg.keys()):
            if key not in merged_ordered:
                del fg[key]

        for key, value in merged_ordered.items():
            if key == "parameters" and isinstance(value, list):
                fg[key] = _merge_parameter_seq(fg.get(key), value)
                continue
            if key in fg and _plain_equal(fg[key], value):
                continue
            fg[key] = _to_yaml_node(value)

        for key in merged_ordered.keys():
            if key in fg:
                fg.move_to_end(key)

        out_data["foreman_hostgroup"] = fg

        buf = StringIO()
        yaml.dump(out_data, buf)
        rendered = buf.getvalue()

    changed = rendered != existing_content

    if changed and not module.check_mode:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)

    module.exit_json(
        changed=changed,
        output_path=output_path,
        diff={"before": existing_content, "after": rendered},
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
