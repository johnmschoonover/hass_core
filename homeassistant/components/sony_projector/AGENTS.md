# Agent Instructions for `sony_projector`

- Always run network operations for this integration via `async_add_executor_job` to avoid blocking the event loop.
- Use the projector host as the config entry unique ID and prevent duplicate flows based on the host.
- Do not ask users to provide a custom name during configuration; rely on the built-in default title instead.
- When writing tests, patch `homeassistant.components.sony_projector.config_flow.pysdcp.Projector` to avoid real I/O.
- Address lint feedback directly instead of suppressing it; avoid adding unnecessary `noqa` directives.
- Enable the config entry flow only when the integration implements `async_setup_entry`/`async_unload_entry` and forwards to the switch platform so UI-configured users get entities immediately.
- The development environment pins Ruff <0.13, so `ruff format` is unavailable—prefer `ruff check --fix` and manual formatting updates when adjusting code here.
