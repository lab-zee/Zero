# Example crews shipped with Zero

These directories are **loadable CrewDefine packages**. `scripts/demo.sh` loads
`technical-due-diligence` by default; pass another directory name to select it.

Canonical authoring copies live in
[CrewDefine](https://github.com/lab-zee/CrewDefine/tree/main/crews). Keep bundled copies in sync
when a reference package changes.

| Directory | Display name | Load |
| --- | --- | --- |
| `technical-due-diligence` | Technical Due Diligence | `./scripts/demo.sh` |
| `business-coaching-crew` | Business Coach | `./scripts/demo.sh business-coaching-crew` |

Revert to the built-in Business Strategy crew:

```bash
./scripts/load-crew.sh --restart --default
```
