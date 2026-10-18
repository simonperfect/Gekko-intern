# Operations runbook template

Complete this template after implementing Module 3. Replace bracketed prompts with tested commands and observed results. Remove these instructions before submission. Run deployment commands from `q3_deploy/` unless a step specifies another directory.

## Start the system

1. Copy `.env.example` to `.env` and set [required configuration values].
2. Run `docker compose up --build`.
3. Check [readiness command]. Expected result: [ready response after the database is reachable].
4. Run `bash scripts/smoke_test.sh` in another terminal. Expected result: [successful batch delivery and recorded receipt].

## Read logs

Run `docker compose logs --tail=100 api mock_ocr mock_onboarding nginx` to inspect recent service logs. Add `-f` to follow new output.

[Record database log access if a separate database service is used. Identify the log fields or messages used to trace a case or export.]

## Diagnose OCR failures

1. Run [command to check the OCR service's `/online` endpoint]. Expected response: `{"online": true}`.
2. Inspect `docker compose logs --tail=100 mock_ocr api` and [command to inspect failed case reasons].
3. Use [recovery command] when the OCR service is unavailable. Use [case recovery action] for timeouts or exhausted retries. An unreadable scan requires a corrected image before processing again.

## Restore a backup

1. Select [backup path] and run [command to stop database writes before restoration].
2. Run [restore command for the chosen database].
3. Run [restart command], then [readiness and restored-data checks]. Expected result: [database reachable and selected backup data present].
