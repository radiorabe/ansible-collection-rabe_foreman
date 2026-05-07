from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "hack"
    / "playbooks"
    / "library"
    / "dump_hostgroup_yaml.py"
)

SPEC = importlib.util.spec_from_file_location("dump_hostgroup_yaml", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ParameterMergingTest(unittest.TestCase):
    def test_preserves_existing_escaped_jinja_in_nested_parameter_value(self):
        yaml = MODULE._yaml_loader()
        existing = yaml.load(
            """
            parameters:
              - name: cockpit_certificates
                parameter_type: yaml
                value:
                  - dns:
                      - "{{ '{{ ansible_host }}' }}"
            """
        )["parameters"]

        merged = MODULE._merge_parameter_seq(
            existing,
            [
                {
                    "name": "cockpit_certificates",
                    "parameter_type": "yaml",
                    "value": [{"dns": ["{{ ansible_host }}"]}],
                }
            ],
        )

        self.assertEqual(
            MODULE._to_plain(merged)[0]["value"][0]["dns"][0],
            "{{ '{{ ansible_host }}' }}",
        )

    def test_updates_non_template_parameter_values(self):
        yaml = MODULE._yaml_loader()
        existing = yaml.load(
            """
            parameters:
              - name: example_secret
                parameter_type: string
                value: old-value
            """
        )["parameters"]

        merged = MODULE._merge_parameter_seq(
            existing,
            [
                {
                    "name": "example_secret",
                    "parameter_type": "string",
                    "value": "new-value",
                }
            ],
        )

        self.assertEqual(MODULE._to_plain(merged)[0]["value"], "new-value")

    def test_updates_when_literal_template_changes(self):
        yaml = MODULE._yaml_loader()
        existing = yaml.load(
            """
            parameters:
              - name: example_secret
                parameter_type: string
                value: "{{ '{{ example_secret }}' }}"
            """
        )["parameters"]

        merged = MODULE._merge_parameter_seq(
            existing,
            [
                {
                    "name": "example_secret",
                    "parameter_type": "string",
                    "value": "{{ different_secret }}",
                }
            ],
        )

        self.assertEqual(
            MODULE._to_plain(merged)[0]["value"],
            "{{ different_secret }}",
        )


if __name__ == "__main__":
    unittest.main()
