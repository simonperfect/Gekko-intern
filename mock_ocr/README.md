# Mock OCR service

The mock represents an identity-card optical character recognition (OCR) vendor and injects transient failures and delayed responses. It requires Python 3.10 or later and uses only the standard library.

## Start the service

From the repository root:

```bash
python3 mock_ocr/server.py
```

The default port is `9100` and the default random seed is `42`. To change the failure sequence:

```bash
python3 mock_ocr/server.py --seed 7
```

The seed reproduces outcomes for a given request sequence. Concurrent requests can change that sequence.

## Request contract

Send `POST /ocr/parse` with a JSON body containing `case_id` and `image_ref`:

```bash
curl --max-time 5 -sS -X POST http://localhost:9100/ocr/parse \
  -H 'Content-Type: application/json' \
  -d '{"case_id": "APPL-2026-0001", "image_ref": "id_scan_0001.jpg"}'
```

HTTP `200` returns these fields:

| Field | Description |
|---|---|
| `id_number` | Synthetic identity number prefixed with `TEST-ID-` |
| `full_name` | Generated name on the identity card |
| `dob` | Date of birth in `YYYY-MM-DD` format |
| `issue_date` | Identity-card issue date in `YYYY-MM-DD` format |
| `confidence` | Numeric confidence value |

The same `image_ref` produces the same parsed fields. Parsing has no billing, callbacks, or other external side effects. Debug records track requests separately from the parsed result.

The example timeout limits the diagnostic request. Measure service behavior before choosing the application's timeout.

## Failure behavior

| Outcome | Service behavior | Client handling |
|---|---|---|
| HTTP `400` | Request JSON is invalid or a required field is missing. | Correct the request. |
| HTTP `500` | The service rejects the attempt before producing a result. | Retry within the application's timeout and retry limits. |
| Delayed response | The service records a `hang` outcome and delays the response for `OCR_HANG_SECONDS`, default `600`. The client can time out without receiving a result. | Treat the result as unknown to the client. Repeating the parse has no external side effects. |
| HTTP `422` | An `image_ref` containing `badscan`, matched without case sensitivity, is unreadable. | Record the service's reason. Repeating the same image cannot resolve the failure. |

Measure observed outcome rates. The configured probabilities and a sample's observed rates are separate values.

## Configuration

| Variable | Description |
|---|---|
| `OCR_PORT` | Listen port. Default `9100`. The `--port` argument overrides this value. |
| `OCR_SEED` | Random seed. Default `42`. The `--seed` argument overrides this value. |
| `OCR_FAIL_RATE` | Probability of a transient HTTP `500` for a readable image |
| `OCR_HANG_RATE` | Probability of a delayed response for a readable image |
| `OCR_HANG_SECONDS` | Response delay for a `hang` outcome, in seconds. Default `600`. |

## Debug endpoints

| Endpoint | Result |
|---|---|
| `GET /debug/requests` | Recorded requests with `seq`, `case_id`, `image_ref`, `outcome`, and `ts` |
| `GET /debug/reset` | Clear the request log |
| `GET /online` | HTTP `200` with `{"online": true}` |

Request outcomes are `ok`, `error_500`, `hang`, or `unreadable`. Requests rejected with HTTP `400` are not recorded. Records are held in memory and cleared on restart.
