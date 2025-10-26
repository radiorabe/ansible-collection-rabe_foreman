#!/usr/bin/python

from __future__ import annotations

from io import StringIO

from ansible.module_utils.basic import AnsibleModule
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString


def _convert_multiline(node):
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, str) and "\n" in value:
                node[key] = LiteralScalarString(value)
            else:
                _convert_multiline(value)
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            if isinstance(value, str) and "\n" in value:
                node[idx] = LiteralScalarString(value)
            else:
                _convert_multiline(value)


def run_module():
    module = AnsibleModule(
        argument_spec={
            "file_paths": {
                "type": "list",
                "elements": "path",
                "required": True,
            },
        },
        supports_check_mode=True,
    )

    file_paths = module.params["file_paths"]

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.explicit_start = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)

    changed = False
    changed_files = []

    for path in file_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                original = f.read()

            data = yaml.load(original)
            if data is None:
                continue

            _convert_multiline(data)

            out = StringIO()
            yaml.dump(data, out)
            rendered = out.getvalue()

            if rendered != original:
                changed = True
                changed_files.append(path)
                if not module.check_mode:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(rendered)
        except Exception as exc:  # pragma: no cover
            module.fail_json(msg=f"Failed to normalize {path}: {exc}")

    module.exit_json(changed=changed, changed_files=changed_files)


def main():
    run_module()


if __name__ == "__main__":
    main()
