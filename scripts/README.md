# Operational Scripts

Utility scripts for developers and system operators. Everything here must read
its configuration from the environment and must work on an isolated network.

Planned (not implemented in Phase 1):

* `dev_setup.sh` — create the virtualenv, install dependencies, copy `.env.example`
* `backup_db.sh` — PostgreSQL dump
* `backup_storage.sh` — archive `storage/letters`
* `create_admin.py` — bootstrap the first administrator account

No scripts are provided yet because they would depend on modules that do not
exist.
