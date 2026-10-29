# Hardware trial contracts

Tests here mock the transport, snapshots and rollback of the opt-in K7 trial
scripts. `python -m unittest` never runs a physical write experiment. Real trials
remain separate explicit commands, subject to the device-specific safety and
approval rules documented in `docs/development/hardware-validation.md`.
