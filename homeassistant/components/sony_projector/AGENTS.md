# Agent Instructions for `sony_projector`

- Always run network operations for this integration via `async_add_executor_job` to avoid blocking the event loop.
- Use the projector host as the config entry unique ID and prevent duplicate flows based on the host.
- Do not ask users to provide a custom name during configuration; rely on the built-in default title instead.
- When writing tests, patch `homeassistant.components.sony_projector.config_flow.pysdcp.Projector` to avoid real I/O.
