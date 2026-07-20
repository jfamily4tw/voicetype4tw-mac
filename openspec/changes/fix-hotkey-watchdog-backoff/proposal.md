# Fix Hotkey Watchdog Backoff

## Why

使用者回報「用一段時間後 key strike 無效，重啟後才恢復」。目前 macOS `CGEventTap` watchdog 在連續 3 次重啟失敗後會停止重試；如果停用是 macOS 暫時狀態或權限服務短暫卡住，app 會一路假死到重啟。

## What Changes

- `hotkey/listener.py` 的 watchdog 不再永久放棄。
- 前 3 次維持每 5 秒重啟，之後改成低頻持續重試，避免洗 log。
- 加 focused unit test 覆蓋 backoff 判斷。
- 版本號更新為 `2.9.17 Coffee Edition / BUILD-2997-RELEASE`，方便本機安裝版與 GitHub release 區分。

## Non-Goals

- 不改熱鍵設定格式。
- 不改錄音、STT、LLM 或貼上流程。
- 不做 release / DMG 打包。
