# Example crews shipped with Zero

These directories are **loadable CrewDefine packages**. `scripts/demo.sh` loads
`business-coaching-crew` into `backend/crews/active/` and starts the stack.

Canonical authoring copy of Business Coach lives in
[CrewDefine](https://github.com/lab-zee/CrewDefine/tree/main/crews/business-coaching-crew).
Keep this tree in sync when the example changes.

| Directory | Display name | Load |
| --- | --- | --- |
| `business-coaching-crew` | Business Coach | `./scripts/demo.sh` or `./scripts/load-crew.sh --restart ./backend/crews/examples/business-coaching-crew` |

Revert to the built-in Business Strategy crew:

```bash
./scripts/load-crew.sh --restart --default
```
