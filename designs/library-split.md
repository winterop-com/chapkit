# Library Split Plan: servicekit (core) + chapkit (ML)

## Executive Summary

**Goal:** Split `chapkit` into two packages - `servicekit` (core framework) and `chapkit` (ML features).

**Approach:** Monorepo with `packages/servicekit` and `packages/chapkit`, using UV workspace.

**Key Insight:** Alembic migrations handled via `alembic_dir` parameter - servicekit keeps existing migrations, chapkit gets empty migration directory for future ML tables. No data migration needed for existing users.

**Timeline:** 4 weeks (branch setup → testing → merge → publish)

**Versioning:** Both packages start at v0.1.0

**Breaking Change:** Import paths only. Database schemas unchanged.

---

## Quick Reference

### Repository Structure
```
chapkit2/
├── packages/
│   ├── servicekit/          # Core framework (no ML dependencies)
│   │   ├── src/servicekit/  # core/, modules/{config,artifact,task}, api/
│   │   ├── alembic/         # Existing migrations (config/artifact/task tables)
│   │   └── tests/
│   └── chapkit/             # ML features (depends on servicekit)
│       ├── src/chapkit/     # ml/, api/ (ML extensions)
│       ├── alembic/         # Empty (future ML tables)
│       └── tests/
├── pyproject.toml           # UV workspace config
└── Makefile                 # Monorepo targets
```

### Import Changes
```python
# Before (v0.1.x)
from chapkit import SqliteDatabase, BaseConfig
from chapkit.modules.ml import MLManager

# After (v0.1.0)
from servicekit import SqliteDatabase, BaseConfig
from chapkit.ml import MLManager
```

### Alembic Strategy
- **servicekit**: Owns existing migrations (config/artifact/task tables)
- **chapkit**: Empty alembic directory, merges servicekit metadata
- **Existing users**: No database migration needed - only update imports

---

## Implementation Phases

### Phase 1: Branch & Monorepo Setup

Create feature branch and monorepo structure:
```bash
git checkout -b feat/split-servicekit
mkdir -p packages/servicekit packages/chapkit
```

Configure UV workspace in root `pyproject.toml`:
```toml
[tool.uv.workspace]
members = ["packages/servicekit", "packages/chapkit"]
```

### Phase 2: Create servicekit Package

**Copy infrastructure:**
- `src/chapkit/core/` → `packages/servicekit/src/servicekit/core/`
- `src/chapkit/modules/{config,artifact,task}/` → `packages/servicekit/src/servicekit/modules/`
- `src/chapkit/api/` → `packages/servicekit/src/servicekit/api/` (exclude ML parts)
- `alembic/` → `packages/servicekit/alembic/`

**Exclude:**
- `modules/ml/` (stays in chapkit)
- ML-specific code: `MLServiceBuilder`, `MLServiceInfo`, `AssessedStatus`

**Update imports:**
- Find/replace: `chapkit.core` → `servicekit.core`
- Update `alembic/env.py`: `from servicekit.core.models import Base`
- Update migration files: `chapkit.core.types` → `servicekit.core.types`

**Create `pyproject.toml`:**
- Core dependencies only (no pandas/scikit-learn)
- Version: `0.1.0`

**Fix bundled migration path in `database.py`:**
```python
# Old: str(Path(__file__).parent.parent.parent.parent / "alembic")
# New:
import servicekit
pkg_path = Path(servicekit.__file__).parent.parent
alembic_cfg.set_main_option("script_location", str(pkg_path / "alembic"))
```

### Phase 3: Create chapkit Package

**Move ML module:**
- `src/chapkit/modules/ml/` → `packages/chapkit/src/chapkit/ml/` (top-level)

**Create ML API layer:**
- Extract ML parts from `api/service_builder.py` to `packages/chapkit/src/chapkit/api/`
- Keep: `ServiceBuilder.with_ml()`, `MLServiceBuilder`, `MLServiceInfo`

**Update imports:**
- Find/replace throughout chapkit:
  - `chapkit.core` → `servicekit.core`
  - `chapkit.modules.{config,artifact,task}` → `servicekit.modules.{config,artifact,task}`
  - `chapkit.modules.ml` → `chapkit.ml`

**Create Alembic environment:**
- Create `alembic/env.py` that merges servicekit and chapkit metadata
- Initially empty `versions/` directory

**Create `pyproject.toml`:**
- Dependency: `servicekit>=0.1.0`
- ML dependencies: `pandas`, `scikit-learn`
- Version: `0.1.0`

### Phase 4: Workspace Configuration

**Root `pyproject.toml`:**
- Workspace members
- Shared tool configs (ruff, mypy, pytest, pyright)

**Root `Makefile`:**
- Targets: `install`, `lint`, `test`, `coverage`
- Per-package targets: `lint-servicekit`, `test-chapkit`, etc.

**Root `README.md`:**
- Document monorepo structure
- Link to package-specific READMEs

### Phase 5: Documentation

**Create package READMEs:**
- `packages/servicekit/README.md`: Core features, installation, quick start
- `packages/chapkit/README.md`: ML features, servicekit dependency, quick start

**Create/update CLAUDE.md:**
- `packages/servicekit/CLAUDE.md`: Core architecture, no ML
- `packages/chapkit/CLAUDE.md`: ML-specific guidance
- Root `CLAUDE.md`: Monorepo overview, link to packages

**Update examples:**
- Copy core examples to `packages/servicekit/examples/`
- Copy ML examples to `packages/chapkit/examples/`
- Update all imports

### Phase 6: Testing & Validation

**Unit tests:**
```bash
make test-servicekit  # Core tests, no ML deps
make test-chapkit     # ML tests with servicekit
make test             # All tests
```

**Migration tests:**
```bash
cd packages/servicekit
uv run alembic upgrade head  # Verify tables created
```

**Type checking:**
```bash
make lint  # Run ruff, mypy, pyright on both packages
```

**Example validation:**
```bash
cd packages/servicekit && uv run fastapi dev examples/config_api.py
cd packages/chapkit && uv run fastapi dev examples/ml_functional.py
```

### Phase 7: CI/CD Updates

**GitHub Actions:**
- Separate jobs for `test-servicekit` and `test-chapkit`
- Shared lint job
- Per-package coverage reports

**Publishing:**
```bash
cd packages/servicekit && uv build && uv publish
cd packages/chapkit && uv build && uv publish
```

### Phase 8: Review & Merge

**Pre-merge checklist:**
- All tests passing
- No linting/type errors
- Documentation complete
- Examples working
- Alembic migrations functional

**Pull request:**
- Title: `feat: split into servicekit (core) and chapkit (ML) packages`
- Include migration guide for users
- Document breaking changes (import paths only)

**Merge:**
```bash
git checkout main
git merge refactor/library-split
git tag servicekit-v0.1.0 chapkit-v0.1.0
git push --tags
```

### Phase 9: Post-Merge

- Publish both packages to PyPI
- Update GitHub repo descriptions
- Create release notes
- Monitor for upgrade issues

---

## Alembic Migration Strategy

### servicekit Migrations

**Location:** `packages/servicekit/alembic/versions/`

**Tables:** `configs`, `artifacts`, `tasks`, `config_artifacts`

**Migration:** `20251010_0927_4d869b5fb06e_initial_schema.py` (existing)

**Auto-run:** Via `Database.init()` with bundled path

### chapkit Migrations

**Location:** `packages/chapkit/alembic/versions/` (empty initially)

**Future tables:** ML-specific models (when needed)

**Metadata merging:** `alembic/env.py` combines servicekit + chapkit Base metadata

**User opt-in:** Specify `with_migrations(alembic_dir=chapkit_path)` if ML tables needed

### User Upgrade Path

**Existing databases (chapkit v0.1.x → servicekit+chapkit v0.1.0):**
```python
# Step 1: Update imports
from servicekit import SqliteDatabaseBuilder  # was: chapkit
from chapkit.ml import MLManager              # was: chapkit.modules.ml

# Step 2: Run application
db = SqliteDatabaseBuilder.from_file("app.db").build()
await db.init()  # Uses servicekit migrations - same tables, no changes needed
```

**No data migration required** - table schemas identical, only import paths change.

---

## Dependencies

### servicekit
- Core: `sqlalchemy`, `aiosqlite`, `alembic`, `pydantic`, `python-ulid`
- FastAPI: `fastapi`, `gunicorn`
- Monitoring: `opentelemetry-*`, `structlog`
- Misc: `geojson-pydantic`
- **Excludes:** pandas, scikit-learn

### chapkit
- Required: `servicekit>=0.1.0`
- ML: `pandas>=2.3.3`, `scikit-learn>=1.7.2`

---

## Key Decisions

### Why Monorepo?
- Atomic refactoring across both packages
- Shared tooling (lint, test, CI)
- Easy integration testing
- Can extract to separate repos later

### Why Keep Migrations in servicekit?
- Existing users have these tables
- No data migration needed
- Clear ownership: servicekit owns core tables
- chapkit can add ML tables independently via separate migrations

### Why Top-Level `chapkit.ml`?
- Clear namespace: ML is obviously in chapkit
- Not a "module" in the same sense as config/artifact/task
- Shorter imports: `from chapkit.ml import ...`

---

## Risk Mitigation

**Import errors during transition:**
- Comprehensive find/replace with regex
- Type checking validates all imports
- Test suite catches missing imports

**Alembic conflicts:**
- Keep servicekit migrations unchanged (same revision IDs)
- Test both migration paths
- Document multi-migration scenarios

**Breaking changes for users:**
- Clear migration guide in PR and release notes
- Version v0.1.0 for both packages (fresh start post-split)
- Data compatibility maintained

**Circular dependencies:**
- Strict dependency direction: chapkit → servicekit only
- Never import ML code in servicekit

---

## Success Criteria

**Functional:**
- servicekit installs without ML dependencies
- chapkit depends on and imports from servicekit
- Existing databases work unchanged
- All tests pass in both packages
- Examples work with new imports

**Non-functional:**
- Clear migration documentation
- Type checking passes across packages
- CI/CD works for both packages
- Publishing process defined

**User experience:**
- Intuitive import paths
- Simple installation (`pip install servicekit` or `pip install chapkit`)
- Clear error messages
- Smooth upgrade path

---

## Timeline

**Week 1:** Phases 1-3 (setup, create packages, move code)
**Week 2:** Phases 4-5 (workspace config, documentation)
**Week 3:** Phase 6 (testing, validation)
**Week 4:** Phases 7-9 (CI/CD, review, merge, publish)

---

## Appendix: Detailed File Operations

### servicekit Package Creation

**Copy operations:**
```bash
cp -r src/chapkit/core packages/servicekit/src/servicekit/
cp -r src/chapkit/modules/{config,artifact,task} packages/servicekit/src/servicekit/modules/
cp -r src/chapkit/api packages/servicekit/src/servicekit/  # Remove ML parts manually
cp -r alembic packages/servicekit/
cp alembic.ini packages/servicekit/
cp -r tests packages/servicekit/  # Remove *ml* tests
```

**Import updates (regex find/replace):**
```regex
from chapkit\.core → from servicekit.core
from chapkit\.modules → from servicekit.modules
import chapkit\.core → import servicekit.core
import chapkit\.modules → import servicekit.modules
```

**Files requiring manual edits:**
- `packages/servicekit/alembic/env.py` (line 13)
- `packages/servicekit/alembic/versions/*.py` (import statements)
- `packages/servicekit/src/servicekit/core/database.py` (bundled path logic)
- `packages/servicekit/src/servicekit/api/service_builder.py` (remove ML classes)

### chapkit Package Creation

**Copy operations:**
```bash
cp -r src/chapkit/modules/ml packages/chapkit/src/chapkit/ml
# Extract ML parts from api/service_builder.py to packages/chapkit/src/chapkit/api/
cp tests/test_*ml* packages/chapkit/tests/
```

**Import updates (regex find/replace):**
```regex
from chapkit\.core → from servicekit.core
from chapkit\.modules\.config → from servicekit.modules.config
from chapkit\.modules\.artifact → from servicekit.modules.artifact
from chapkit\.modules\.task → from servicekit.modules.task
from chapkit\.modules\.ml → from chapkit.ml
```

**Create alembic environment:**
```bash
mkdir -p packages/chapkit/alembic/versions
# Create env.py with metadata merging
# Create alembic.ini
```

---

## Decisions Made

1. **Package name:** `servicekit` (confirmed)
2. **Versioning:** Both packages at v0.1.0 (fresh start)

## Questions to Resolve

1. Long-term: keep monorepo or extract to separate repos?
2. Publishing: independent or synchronized releases?
3. Backward compatibility: deprecation warnings for old imports?

---

## Next Steps

1. Answer remaining questions
2. Begin Phase 1: Monorepo setup
3. Iterate based on discoveries during implementation
