# Ansible Role - radiorabe.rabe_foreman.infrastructure

Manages Infrastructure in Foremans using Foreman.

## Role Variables

This role does not expose any variables.

## Dependencies

The `radiorabe.rabe_foreman.content` role depends on the [`theforeman.foreman`](https://galaxy.ansible.com/theforeman/foreman) and [`radiorabe.foreman`](https://galaxy.ansible.com/radiorabe/foreman) collections.

## Example Playbooks

```yaml
- name: Configure Foreman Infrastructure
  hosts: localhost
  gather_facts: false
  roles:
    - role: radiorabe.rabe_foreman.infrastructure
```

## License

This role is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, version 3 of the License.
