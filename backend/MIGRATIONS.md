# Database migrations

**Alembic is the single source of truth for the schema.** The app no longer calls
`Base.metadata.create_all()` on startup — deploys run `alembic upgrade head` (see
`start.sh`).

## Why this changed

The old setup ran **both** `create_all()` (which built tables from the models on every
boot) **and** Alembic migrations. `create_all` created columns ahead of the migrations,
so migrations like `add_execution_trace` then failed with `DuplicateColumn`, and Alembic
got stuck — every migration behind the failure stopped applying. The two systems were
fighting. We collapsed to one: **models → Alembic → database.**

The 17 pre-existing migrations were moved to `alembic/_archived_versions/` (kept for
reference only; Alembic does not load them) and replaced by a single baseline.

---

## Finishing this branch (one-time)

The baseline migration must be generated against an **empty** database so it captures the
full current schema. Do this locally, then reconcile prod.

### 1. Generate the baseline

```bash
cd backend
# spins up a throwaway Postgres, autogenerates the baseline, tears it down
./scripts/gen-baseline.sh
```

Or manually, against any empty Postgres:

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/scratch_empty_db
alembic revision --autogenerate -m "baseline schema"
```

### 2. Review the generated file (important)

Open the new file in `alembic/versions/`. Autogenerate can miss things — confirm it
includes **every** table and column your models define, plus:

- `server_default`s (e.g. `now()` timestamps, boolean defaults)
- JSON vs **JSONB** column types
- indexes, unique constraints, foreign keys
- the `custom UUID`/`JSON` `TypeDecorator`s in `models.py`

Compare against `models.py`. Hand-edit the migration to fix anything missing.

### 3. Verify on a fresh database

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/scratch_fresh_db  # empty
alembic upgrade head
# then diff this schema against prod (or against models) — they must match
```

If the app boots and the schema is complete, the baseline is good.

### 4. Reconcile production (schema already exists there)

Prod already has the full schema (built by the old `create_all`). **Do not run
`upgrade`** against it — stamp it as already-applied:

```bash
# one-off against the prod DB (Railway backend service has DATABASE_URL)
railway run --service <backend> alembic stamp head
```

Now Alembic's version pointer matches reality; future deploys `upgrade head` cleanly
(a no-op on prod, a full build on any fresh DB).

### 5. Merge

Merge the branch. The next deploy runs `alembic upgrade head` and succeeds.

---

## Day-to-day workflow (after this)

1. Change a model in `src/models.py`.
2. `alembic revision --autogenerate -m "describe the change"`.
3. **Review** the generated migration — autogenerate is a draft, not gospel.
4. Commit it with the model change.
5. Deploy → `start.sh` runs `alembic upgrade head`.

New model? Make sure it's imported in `alembic/env.py` (importing anything from
`src.models` registers all classes in that module, so keep models in one file or import
new modules there).

## Notes

- `start.sh` currently does `alembic upgrade head || echo "..."`, which swallows failures
  so a bad migration won't crash boot. Once the baseline is in, consider tightening this
  to surface migration errors.
- Never reintroduce `create_all()` — it's what caused the drift.
