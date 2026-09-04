# Public multi-repository coding benchmark

This comparison uses synthetic regression tasks on pinned public repository snapshots. It intentionally excludes prompts, repository snapshots, patches, test output, error details, and credentials.

| Repository | Task | Provider | Model | Status | Patch | Tests | Time (s) |
|---|---|---|---|---|---|---|---:|
| [pallets/click](https://github.com/pallets/click) | Preserve the double-dash option prefix | codex-cli | gpt-5.6-luna | passed | yes | yes | 10.976 |
| [pallets/click](https://github.com/pallets/click) | Preserve the double-dash option prefix | claude-cli | sonnet | error | no | no | 180.107 |
| [psf/requests](https://github.com/psf/requests) | Preserve case-insensitive header lookup | codex-cli | gpt-5.6-luna | passed | yes | yes | 4.681 |
| [psf/requests](https://github.com/psf/requests) | Preserve case-insensitive header lookup | claude-cli | sonnet | passed | yes | yes | 15.105 |

Each row is evidence for one task; these results are not a universal model ranking.
