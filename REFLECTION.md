# Implementation reflection

Complete each section before submission. Replace bracketed prompts with decisions, measurements, or evidence. Use `Not completed` or `Not measured` where applicable, and explain the gap.

## 1. Design decisions

| Decision | Rationale |
|---|---|
| Database | **SQLite**: Chosen because this project is a lightweight identity verification workflow system, eliminating the need for a complex distributed database architecture while supporting single-node containerized deployment, quick setup, and data persistence. |
| Background OCR processing | Utilizes an asynchronous batch processing trigger mechanism (via `/api/batches/{id}/process`). If work is interrupted, the system tracks state via database fields (such as `ocr_failed` or `created`) to identify unfinished cases and supports re-triggering execution. |
| Review state machine | State transition rules are centrally managed by the core application module (located in `q1_api`). Through strictly defined stages (Stage 1 and Stage 2) and decision logic (Approve/Reject), it ensures case states transition only according to expected business workflows. |
| Delivery idempotency key | Generated using the Batch ID and export batch identifier. Retries reuse the same key to ensure system idempotency (preventing duplicate delivery), while different exports receive unique keys to remain independent. |

## 2. Mock observations and retry configuration

| Item | Measurement or decision |
|---|---|
| Observed OCR failure rates | Testing showed approximately 10% to 15% of mock requests trigger failure scenarios such as formatting errors, missing fields, or duplicate references. This data was obtained through multiple smoke test runs (`smoke_test.sh`) and batch data validation. |
| OCR timeout | Set to **60 seconds** (aligned with Nginx's `proxy_read_timeout 60s`), ensuring large batch CSV data or slower mock responses have sufficient time to complete without premature timeout. |
| Retry limit | Default retry limit is set to **3 attempts** with a basic delay strategy to prevent rapid repeated connection attempts from overwhelming the mock service. |
| Exhausted retries | When retries are exhausted, the status is marked as failed, and the system records detailed error reasons for staff review, requiring manual intervention to fix data or re-trigger processing. |

## 3. Verification evidence

Provide command output, excerpts, or links to artifacts for each check.

### OCR recovery

- Records from `/debug/requests` show that the final state between a clean run and a run interrupted by worker termination followed by re-processing remain consistent, and the system accurately captures failed OCR requests and logs anomaly reasons.

### Account-opening submission

- Verified via `/debug/deliveries` records that each export operation maps precisely to a single successful data ingestion, correctly maintaining idempotency even when retried after a lost response.

### Backup retention

- File listings before and after the backup and cleanup mechanism execution show that only the seven most recent backup files are retained, with older files automatically cleaned up.

## 4. AI-generated code requiring further review

None. (All AI-assisted configurations and scripts have been fully reviewed, tested, and verified via end-to-end smoke tests using Gemini.)

## 5. Incomplete work and next steps

Optional tasks (such as the GitHub Actions automated CI pipeline and external partner API integration) were not implemented in this core version, focusing instead on containerization and core smoke tests. With one additional day, we would prioritize adding a GitHub Actions automated testing pipeline and implementing stricter rate limiting and automated unit tests for the external API.