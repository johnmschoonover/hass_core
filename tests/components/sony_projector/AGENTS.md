# Sony Projector test guidelines

- Prefer `MockConfigEntry` from `tests.common` to construct entries for this integration.
- Patch or stub out `ProjectorClient` interactions with `AsyncMock` objects; never import or rely on the real `pysdcp` library in tests.
- Use the shared `conftest.py` stub for `pysdcp` so tests never import the real dependency or duplicate stubbing logic.
- When asserting repairs issues, inspect the awaited call arguments (for example, `mock_issue.await_args`) instead of relying on private attributes.
