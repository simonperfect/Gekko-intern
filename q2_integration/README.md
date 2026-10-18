# Module 2: OCR integration and export delivery

Add OCR, export, and delivery modules to `q1_api/app/`. Register the new endpoints on the existing `app.main:app` application. Keep the [fixed repository layout](../README.md#2-fixed-structure-and-naming).

Read the [Module 2 requirements](../README.md#4-module-2-ocr-integration-and-export-delivery), [OCR contract](../mock_ocr/README.md), and [account-opening contract](../mock_onboarding/README.md) before implementing the clients.

## Run without Docker

Start each service in a separate terminal from the repository root:

```bash
python3 mock_ocr/server.py
```

```bash
python3 mock_onboarding/server.py
```

```bash
cd q1_api
uvicorn app.main:app --reload
```

Configure the API to use `http://localhost:9100/ocr/parse` and `http://localhost:9200/ingest`. Document the API configuration method after implementation.

Verify one batch through import, background OCR, both review stages, export, and submission to the account-opening service. Record retry and recovery evidence in [REFLECTION.md](../REFLECTION.md).
