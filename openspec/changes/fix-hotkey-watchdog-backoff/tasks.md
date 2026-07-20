## 1. Diagnose

- [x] 1.1 Inspect current app logs for CGEventTap disable / watchdog signals.
- [x] 1.2 Confirm current code can stop retrying after consecutive disabled checks.

## 2. Implement

- [x] 2.1 Add watchdog backoff constants and retry decision helper.
- [x] 2.2 Keep retrying disabled CGEventTap at low frequency after the initial burst.
- [x] 2.3 Preserve existing state reset behavior after re-enable attempts.

## 3. Verify

- [x] 3.1 Add focused unit test for watchdog retry cadence.
- [x] 3.2 Run focused hotkey listener test.
- [x] 3.3 Run py_compile for touched modules.
