# Mock account-opening service

The mock receives approved identity-verification applications for the securities platform's account-opening workflow. It injects transient failures and delayed responses after ingestion. It requires Python 3.10 or later and uses only the standard library.

## Start the service

From the repository root:

```bash
python3 mock_onboarding/server.py
```

The default port is `9200` and the default random seed is `7`. Use `--port` or `--seed` to override them. The seed reproduces outcomes for a given request sequence.

## Ingestion contract

Send `POST /ingest` with the file bytes as the request body:

```bash
curl --max-time 5 -sS -X POST http://localhost:9200/ingest \
  -H 'Idempotency-Key: my-export-key' \
  -H 'X-File-Name: EXPORT-APPL-001.csv' \
  --data-binary @some_file.csv
```

Replace `some_file.csv` with the export file. The example timeout limits the diagnostic request. Select the application's timeout based on observed behavior.

| Header | Requirement |
|---|---|
| `Idempotency-Key` | Required. Identifies one export delivery across all attempts. |
| `X-File-Name` | Filename recorded in the receipt. Defaults to `unnamed` if omitted. |

Each successful ingestion represents one submission of approved applications to the account-opening workflow. Duplicate ingestion submits the applications again. The mock records submissions and receipts. The ingestion API provides no cancellation operation.

The service deduplicates by `Idempotency-Key`. A repeated key returns the original receipt with `"deduplicated": true` and does not ingest another file. Deduplication uses the key alone. Sending different bytes with an existing key still returns the original receipt.

Keep the same key when retrying one export. Use a different key for a different export.

HTTP `200` returns a receipt with these fields:

| Field | Description |
|---|---|
| `delivery_id` | Identifier assigned to the ingestion |
| `idempotency_key` | Supplied delivery key |
| `file_name` | Supplied filename or `unnamed` |
| `sha256` | SHA-256 hash of the ingested bytes |
| `ingested_at` | Ingestion time as Unix seconds |
| `attempts` | Initial ingestion plus requests deduplicated against the receipt. Failed attempts before ingestion are excluded. |

## Failure behavior

| Outcome | Service behavior | Client handling |
|---|---|---|
| HTTP `400` | `Idempotency-Key` is missing. No ingestion occurs. | Add the required header. |
| HTTP `500` | The service rejects the attempt without recording an ingestion. | Retry with the same export key. |
| Delayed response | Ingestion is recorded before the response is delayed by `ONBOARDING_LOST_SECONDS`, default `120`. The client can time out after ingestion succeeds. | Retry with the same export key to retrieve the receipt without another ingestion. |

## Configuration

| Variable | Description |
|---|---|
| `ONBOARDING_PORT` | Listen port. Default `9200`. The `--port` argument overrides this value. |
| `ONBOARDING_SEED` | Random seed. Default `7`. The `--seed` argument overrides this value. |
| `ONBOARDING_FAIL_RATE` | Probability of HTTP `500` for a key that has not been ingested |
| `ONBOARDING_LOST_RATE` | Probability of a delayed response after a new ingestion |
| `ONBOARDING_LOST_SECONDS` | Delay after ingestion, in seconds. Default `120`. |

## Debug endpoints

| Endpoint | Result |
|---|---|
| `GET /debug/deliveries` | One receipt per ingestion, with the fields listed above |
| `GET /debug/reset` | Clear delivery records and idempotency keys for a new test |
| `GET /online` | HTTP `200` with `{"online": true}` |

Delivery records and idempotency keys are held in memory and cleared on restart. Retain the records while testing retries for an export. Use `GET /debug/deliveries` to verify one ingestion per export.
