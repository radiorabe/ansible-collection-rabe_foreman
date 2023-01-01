# Ansible Collection - radiorabe.rabe_foreman

GitOps our Foreman. This is where most of our Foreman configuration lives.

## Roles

* [`client`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/client) Configure attached systems (this is the only role that is run everywhere, the others are specific to the server)
* [`content`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/content) Put Content into Foreman
* [`foreman`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/foreman) Administer and Configure Foreman
* [`infrastructure`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/infrastructure) Infrastruture
* [`hosts`](https://github.com/radiorabe/ansible-collection-rabe_foreman/tree/main/roles/hosts) Provisioning Setup and Templates

## Development

### Adding a Product and Repositories

* add the product and repo in `roles/content/tasks/products.yaml`
* if creating a new product, add it in `roles/content/tasks/sync_plans.yaml`
* add the new repo to the corresponding "Base" repo or create a new view in `roles/content/tasks/content_views.yaml`
* if you created a new view add it to `playbooks/content_view_publish.yml` and `playbooks/content_view_promote.yml`
* disable the new repo in all relevant activation keys or create a new key in `roles/content/tasks/activation_keys.yaml`
  * your content views need to be published to Prod for this step! this isn't currently automated

## License

This collection is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, version 3 of the License.
