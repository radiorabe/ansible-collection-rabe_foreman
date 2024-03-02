# Ansible Collection - radiorabe.rabe_foreman

GitOps our Foreman. This is where most of our Foreman configuration lives.

## Usage

### Roles

* [`client`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/client) Configure attached systems (this role run everywhere, most the others are specific to the server)
* [`content`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/content) Put Content into Foreman
* [`foreman`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/foreman) Administer and Configure Foreman
* [`hosts`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/hosts) Provisioning Setup and Templates
* [`infrastructure`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/infrastructure) Infrastruture
* [`network`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/network) (This role wraps `rhel.rhel_system_roles.network` so we can use ansible facts for network configuration and is run on all hosts.)

### Playbooks

* [RaBe Foreman Playbooks : Content View Promote](https://github.com/radiorabe/ansible-collection-rabe_foreman/blob/main/playbooks/content_view_promote.yml)
* [RaBe Foreman Playbook : Content View Publish](https://github.com/radiorabe/ansible-collection-rabe_foreman/blob/main/playbooks/content_view_publish.yml)
* [RaBe Foreman Playbook : Content View Version Cleanup](https://github.com/radiorabe/ansible-collection-rabe_foreman/blob/main/playbooks/content_view_version_cleanup.yml)

## Development

### Adding a Product and Repositories

* add the product and repo in `roles/content/tasks/products.yaml`
* if creating a new product, add it in `roles/content/tasks/sync_plans.yaml`
* add the new repo to the corresponding "Base" repo or create a new view in `roles/content/tasks/content_views.yaml`
* if you created a new view add it to `playbooks/content_view_publish.yml` and `playbooks/content_view_promote.yml`
* disable the new repo in all relevant activation keys or create a new key in `roles/content/tasks/activation_keys.yaml`
  * your content views need to be published to Prod for this step! this isn't currently automated

### Removing old Products

Products are removed once they are not in active use by any content view. Hence deprovisioning a component needs to be done in stages:

* remove the product from `roles/content/tasks/content_views.yaml` and from the publish and promote playbooks in `playbooks/`
* at this stage, there are probably still active users of the old content view so we wait until a new version of the content view is released and they are life cycled
* once there are no more active users, we can stop syncing the product since we don't need updated errata anymore, we remove it from `roles/content/tasks/sync_plans.yaml`
* at this point, there are still old versions of content views that may contain the product. it will take a while until `playbooks/content_view_version_cleanup.yml` removes them
* after checking that there are no more dependencies on the product, they get changed to `state: absent` in `roles/content/tasks/products.yaml` removing them from our foreman, at this point the list of repositories is also removed from the file
* Once they are gone from Foreman they can be removed from this repo with the next major release (or any 0.x release)

## License

This collection is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, version 3 of the License.
