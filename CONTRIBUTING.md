# 一起共創嘴炮輸入法

謝謝你想一起把 VoiceType4TW 嘴炮輸入法變得更好。這個專案採用 MIT 授權，歡迎研究、修改、分享與送 Pull Request。

## 可以怎麼參與

- 回報 bug：請到 GitHub Issues 說明作業系統、版本、重現步驟、預期結果與實際結果。
- 提功能建議：請先開 Issue 描述使用情境，讓大家先對齊方向。
- 修文件：拼字、安裝步驟、疑難排解、截圖說明都很歡迎。
- 修程式：請先 fork 專案，開新 branch，完成後送 Pull Request。

## Issue 建議格式

請盡量包含：

- 使用平台：macOS 或 Windows，以及系統版本。
- 嘴炮輸入法版本：例如 `2.9.17 Coffee Edition`。
- 問題描述：發生了什麼、多久發生一次。
- 重現步驟：一步一步列出如何看到問題。
- Log 或截圖：若方便，請附上相關片段；不要貼 API key、token、私人資料。

## Pull Request 建議流程

1. Fork 這個 repo。
2. 從目標分支建立新 branch，例如 `fix/hotkey-watchdog` 或 `docs/install-notes`。
3. 保持修改範圍小而清楚；文件、macOS code、Windows code 盡量不要混在同一個 PR。
4. 能測的話請先跑相近測試、lint、build 或 smoke check，並在 PR 描述寫明結果。
5. 開 Pull Request，說明你改了什麼、為什麼改、如何驗證。

## 分支說明

- `main`：macOS 版本主要分支。
- `win-stable`：Windows 穩定版本分支。
- 其他 Windows 實驗分支若要合併，請先開 Issue 或 PR 討論目標版本與影響範圍。

## 行為與安全

- 請尊重不同使用者與貢獻者的使用情境，討論時聚焦在問題與解法。
- 不要提交 API key、私密 log、個人資料或大型模型 cache。
- 若發現安全性問題，請先用 Issue 以外的私下管道聯絡維護者，避免公開可被濫用的細節。
