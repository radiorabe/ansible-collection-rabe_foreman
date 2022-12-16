# Ansible Role - radiorabe.rabe_foreman.client

Manages Systems attached to our Foreman.

## Role Variables

This role does not expose any variables.

## Dependencies

The `radiorabe.rabe_foreman.client` role does not have any depdendencies.

## Example Playbooks

```yaml
- name: Configure Foreman Client
  hosts: localhost
  gather_facts: false
  roles:
    - role: radiorabe.rabe_foreman.client
```

## License

This role is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, version 3 of the License.
