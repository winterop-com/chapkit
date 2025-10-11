## Examples

The `examples/` directory contains small, self-contained scripts that demonstrate how to use Chapkit’s managers.

- `config_example.py` shows how to define a custom `BaseConfig` payload, persist it via `ConfigManager`, and fetch it back by name.
- `artifact_example.py` builds a tiny artifact tree, passes an `ArtifactHierarchy` into `ArtifactManager`, and prints each artifact with its persisted level plus hierarchy-derived labels.

To run an example, make sure dependencies are installed (e.g., `make install`), then execute:

```bash
uv run python examples/config_example.py
# or
uv run python examples/artifact_example.py
```
