# Module 1: Core API

Implement the API in `app/` and tests in `tests/`. Keep the entry point importable as `app.main:app`. Organize database access, validation, and transition rules into modules within `app/`.

The [Module 1 requirements](../README.md#3-module-1-core-api) define endpoints, review behavior, and test coverage. The [repository layout](../README.md#2-fixed-structure-and-naming) defines fixed paths and names.

## Start the API

From the repository root:

```bash
python -m pip install -r requirements.txt
cd q1_api
uvicorn app.main:app --reload
```

The scaffold exposes `GET /api/health`. Complete the remaining endpoints before testing the application workflow.

## Run tests

From the repository root:

```bash
python -m pytest q1_api/
```

Replace the scaffold import test with tests covering the required behavior. The suite must pass from a clean checkout.
