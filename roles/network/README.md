# Ansible Role - radiorabe.rabe_foreman.network

Calls the the [network](https://galaxy.ansible.com/linux-system-roles/network)
role with a `network_connections` variable based on the `foreman_interfaces`
parameter so we can configure interfaces via Foreman.

The heavy lifting is done in [templates/network-connections.j2](./templates/network-connections.j2)
in what might be considered a rather hacky template.

## Role Variables

This role reads the `foreman_interfaces` fact as well as facts from `radiorabe.common.core`

The `radiorabe_rabe_foreman_network_dns_vip` variable is local to this role for now.

## Dependencies

The `radiorabe.rabe_foreman.network` role depends on these roles:
* `radiorabe.common.core`
* `redhat.rhel_system_roles.network`

## Example Playbooks

```yaml
- name: Configure Network
  hosts: localhost
  gather_facts: false
  roles:
    - role: radiorabe.rabe_foreman.network
      vars:
        # This is defined by Foreman!
        foreman:
          foreman_interfaces:
            - identifier: "enp1s0"
              name: test-0000.service.int.example.org
              attrs:
                type: "ether"
                ipv4:
                  address: "10.131.0.100"
                  network: "10.131.0.0"
                  prefix: "16"
```

## License

This role is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, version 3 of the License.
