# Public multi-repository coding benchmark

This comparison uses synthetic regression tasks on pinned public repository snapshots. It intentionally excludes prompts, repository snapshots, patches, test output, error details, and credentials. Claude input-token values include uncached, cache-read, and cache-created tokens reported for the selected model.

| Repository | Task | Provider | Model | Status | Patch | Tests | Time (s) | Input tokens | Output tokens |
|---|---|---|---|---|---|---|---:|---:|---:|
| [pallets/click](https://github.com/pallets/click) | Preserve the double-dash option prefix | codex-cli | gpt-5.6-luna | passed | yes | yes | 13.299 | 41958 | 774 |
| [pallets/click](https://github.com/pallets/click) | Preserve the double-dash option prefix | claude-cli | sonnet | passed | yes | yes | 24.629 | 10001 | 1593 |
| [psf/requests](https://github.com/psf/requests) | Preserve case-insensitive header lookup | codex-cli | gpt-5.6-luna | passed | yes | yes | 5.045 | 10429 | 311 |
| [psf/requests](https://github.com/psf/requests) | Preserve case-insensitive header lookup | claude-cli | sonnet | passed | yes | yes | 11.375 | 5912 | 648 |

Each row is evidence for one task; these results are not a universal model ranking.
