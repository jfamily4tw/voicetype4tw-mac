# VoiceType4TW 開發版本全紀錄 (面向物件分析)

本檔案用於精確紀錄「使用者需求」與「實際變更」的對照，並連結至 Git 提交與備份紀錄。最新版本置頂。

---

## [v2.9.19] - 2026-07-23 (Coffee Hotfix)
### Apple Local prompt leak 防漏修復
- **Prompt leak 防線**：修正 Apple Foundation Models 偶發回吐提示詞模板，造成輸入框貼出「原文 / 校正後文字」與 Markdown code fence 的問題。
- **輸出清洗**：Python wrapper 會先抽取 `校正後文字` 區塊；若仍偵測到提示詞模板或 code fence，就回退到原始 STT 校正版，避免 prompt 被貼出。
- **Prompt 降風險**：Swift helper 改成更短的 user prompt，並明確禁止輸出標籤、引號、Markdown 或說明。
- **資料清理**：本機 `memory.json` 與 `auto_memory.json` 已移除本次 prompt leak 污染詞與污染紀錄，保留乾淨口述內容。

| 項目 | 值 |
|------|-----|
| BUILD_ID | `BUILD-2999-HOTFIX` |
| Coffee Edition DMG | `嘴炮輸入法_v2.9.19-Coffee-Edition_macOS.dmg` |

---

## [v2.9.18] - 2026-07-21 (Coffee Release)
### Apple Local 本機快速校正與簡繁保險
- **本機快速校正**：新增 Apple Foundation Models helper，支援在 STT 後用 Apple Local 進行快速校正。
- **模式拆分**：新增「本機快速校正（Apple Local）」獨立開關，與「AI 潤飾/翻譯」分離；本機校正只做文字校正，不套用雲端 LLM 靈魂。
- **選單控制**：Menu Bar 新增本機快速校正 ON/OFF，方便即時切換。
- **簡繁保險**：加入 OpenCC 簡轉繁後處理，修正 Whisper 偶發輸出 `列进来`、`协助开发者` 等簡體字。
- **句尾保護**：Apple Local helper 加強保留既有句號、問號、驚嘆號與口語問句標點；LLM 未啟用時仍保留既有輕量版靈魂規則。
- **詞彙修復**：短英文縮寫不再被模糊詞彙修正誤改，避免 `STT` 被改成 `PTT`。
- **打包更新**：build 流程會先編譯 Apple Local helper，並將 helper 與 OpenCC 一起納入 app bundle。

| 項目 | 值 |
|------|-----|
| BUILD_ID | `BUILD-2998-RELEASE` |
| Coffee Edition DMG | `嘴炮輸入法_v2.9.18-Coffee-Edition_macOS.dmg` |

---

## [v2.9.16] - 2026-05-24 (Coffee Release)
### 長靜音幻覺與翻譯模式污染修復
- **長靜音幻覺過濾**：新增高比例重複 token / n-gram 偵測，阻擋「通過」連發、`anterior access` 長尾重複等 Whisper 靜音幻覺。
- **YouTube 結尾變體擴充**：補上「多謝您的觀看」等中文 / 粵語式結尾片語，修正 30 秒純靜音會輸出的案例。
- **STT 語言選擇修復**：STT 辨識語言改用 `config.language`，不再被 `translation_lang=en` 污染，避免回英文信後中文錄音後半段漂成英文。
- **模型搬遷**：`mlx-community/whisper-medium-mlx` Hugging Face cache 可搬到外部模型快取目錄，原 cache 位置保留 symlink。
- **驗證**：30 秒純靜音 STT 回空字串；source app 與 dist app 均可透過外部模型快取 symlink 載入模型並進入 `Models are READY`。

| 項目 | 值 |
|------|-----|
| BUILD_ID | `BUILD-2996-RELEASE` |
| Coffee Edition DMG | `嘴炮輸入法_v2.9.16-Coffee-Edition_macOS.dmg` |

---

## [v2.8.2] - 2026-03-04 19:00 (Stable Release)
### 全功能同步與對齊 (Full Parity)
- **旗艦功能對齊**：同步 Mac 版的高精度「處理耗時顯示」與「執行日誌系統」。
- **API Key 預檢機制**：增加強健性檢查，若 API Key 未填將在 MicIndicator 顯示紅色警告，防止測試閃退。
- **雙層設定架構 (Double-Layer Config)**：
  - `config_local.json`：存放熱鍵、硬體特定設定（不參與同步）。
  - `config_global.json`：存放 API Keys、Prompt（參與同步）。
- **NAS 指標同步**：實作 `sync_path.txt` 目錄重定向，支援 NAS 私密靈魂同步。
- **穩定性修補**：移除 PC 版過時的 `CONFIG_PATH` 依賴。

---

## [v2.8.1-dev] - 2026-03-04 11:15 (Cloud Sync Handover)
### 🚀 跨平台同步開發
- **核心實作**：
  - `paths.py`：實作 `get_sync_base_dir()` 透過指標重定向資料目錄。
  - `config.py`：實作 `LOCAL_KEYS` 白名單，正式拆分 Local 與 Global 設定。
- **UI 強化**：新增 [☁️ 雲端同步] 專屬分頁，支援遷移與連結 NAS 目錄。

---

## [v2.8.0] - 2026-03-03 18:30 (Official PC Release B19)
### 核心穩定性與瀏覽器解禁
- **瀏覽器輸入修復 (B19)**：徹底移除針對瀏覽器的注入攔截，實現全網頁通用輸入。
- **極簡托盤選單 (B16)**：將模式與情境選擇移至浮動按鈕，托盤僅保留基礎設定。
- **浮動按鈕切換 (B18)**：支援使用者自定義開啟/關閉浮動按鈕 UI。
- **啟動防護與穩定性**：解決了 Windows 下的 OpenMP 衝突與 Pystray 死鎖，Build 躍升至 B19。

---

## [v2.7.32 B15] - 2026-03-03 15:00 (Tray Sync Fix)
- **托盤選單修復**：解決 Windows 下儲存設定後圖示選單更新失敗的问题。

---

## [v2.7.32 B14] - 2026-03-03 14:20 (Log Cleanup)
- **日誌淨化**：改進層級控制，關閉 Debug 時不再輸出大量熱鍵日誌。

---

## [v2.7.32 B8-B13] - 2026-03-03 (Security & UX Polish)
- **B13 (Hotfix)**：修正 SettingsWindow 崩潰。
- **B12 (Separate Log)**：實作 `keystrike.log` 職責分離。
- **B11 (Dynamic Prefix)**：前綴改為動態的情境名稱。
- **B10 (Build ID System)**：引入 `paths.py` 硬編碼 Build ID 追蹤。
- **B8-B9 (Memory Sync)**：引入 `<Draft>` XML 標籤保護與 `AI_MEMORY.md` 雙層架構。

---

## [v2.7.32 B7] - 2026-03-03 10:00 (Prompt Alignment)
- **Prompt 結構優化**：規則前置、資料後置。強制半形括號 `[]` 與標點符號風格鎖定。

---

## [v2.7.32 B2-B6] - 2026-03-03 09:00 (Flagship Features)
- **B6 (NameError Fix)**：修復 Demo 模式變數遺漏。
- **B5 (Format Fix)**：校準 `[底層靈魂]` 標籤格式。
- **B4 (UI Alignment)**：整合 Demo 控制項至系統設定頁。
- **B2-B3 (Scenario Loop)**：實作遍歷所有性格的測試模式並優化選單勾選。

---

## [v2.7.32 beta] - 2026-03-02 22:00 (Windows Porting Start)
- **啟動加強**：強制 `KMP_DUPLICATE_LIB_OK=TRUE`。
- **導入優化**：採用延遲導入 (Lazy Import) 避免重複依賴。
- **路徑重組**：將資料路徑導向 `%APPDATA%/VoiceType4TW`。

---

## [v2.7.24-pc-stable] - 2026-03-01 18:00 (Stable Base)
- **Windows 初心版**：建立能在 PC 穩定執行的環境基準，包含 Inno Setup 安裝配置。
