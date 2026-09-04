# Public multi-repository coding benchmark

This comparison uses synthetic regression tasks on pinned public repository snapshots. It intentionally excludes prompts, repository snapshots, patches, test output, error details, and credentials.

| Repository | Task | Provider | Model | Status | Patch | Tests | Time (s) | Input tokens | Output tokens |
|---|---|---|---|---|---|---|---:|---:|---:|
| [pallets/click](https://github.com/pallets/click) | Preserve the double-dash option prefix | codex-cli | gpt-5.6-luna | passed | yes | yes | 6.244 | 13781 | 344 |
| [pallets/click](https://github.com/pallets/click) | Preserve the double-dash option prefix | claude-cli | sonnet | passed | yes | yes | 13.112 | 2 | 839 |
| [psf/requests](https://github.com/psf/requests) | Preserve case-insensitive header lookup | codex-cli | gpt-5.6-luna | passed | yes | yes | 9.597 | 42896 | 595 |
| [psf/requests](https://github.com/psf/requests) | Preserve case-insensitive header lookup | claude-cli | sonnet | passed | yes | yes | 11.314 | 2 | 699 |

Each row is evidence for one task; these results are not a universal model ranking.
