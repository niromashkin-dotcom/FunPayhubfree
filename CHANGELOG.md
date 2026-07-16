# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] (Dev)

### Fixed
- **VPS Deployment (Systemd Services)**: Split the monolithic `funpayhub.service` into two separate services:
  - `funpayhub-core.service`: Runs the Flask Core API via gunicorn on `127.0.0.1:5000`.
  - `funpayhub.service`: Runs the Telegram Bot (`run_bot.py`) and now depends on `funpayhub-core.service` (`After=network.target funpayhub-core.service`).
  *This fixes the cyclic crash where the Telegram Bot could not connect to the backend (Timeout Error).*
- **VPS Setup Script (Root Lockout)**: Fixed a bug in the setup scripts where `PermitRootLogin no` was aggressively set in `sshd_config`, causing the VPS owner to be locked out of the server after SSH restart.

### Known Issues
- `hub_bootstrap.py` (Line 480): `NameError: name 'hub_url' is not defined` occurs in `_start_market_auto_update` because `hub_url` is not passed to the background thread. This crashes the market update thread but does not affect the core application loop.
