# VoiceType4TW 嘴炮輸入法 — Windows 專用版 (win-go-mask v3.0.1)

主要開發者：吉米丘 , CC58TW 
協助開發者：Claude Code

吉米與女兒CC58TW全新開發的嘴炮輸入法，讓你出一張嘴就能打字的輸入法

> **📌 本 repo 為 Windows 10/11 專用開發版**（win-stable 分支），已移除所有 macOS 專屬程式碼與打包腳本，針對 Windows 環境深度優化安裝與相容性。
> macOS 版請見原作者專案：[jfamily4tw/voicetype4tw-mac](https://github.com/jfamily4tw/voicetype4tw-mac)

免費版歡迎大家測試使用，GitHub開源的Python版，想自己抓下來研究、裝在電腦裡都OK


目前有PC有兩個版本：

Github版：原始碼全部開源，想玩的自己去下載安裝，完全免費，但無法提供繼續支援，需要麻煩各位高手自己研究解決

![批次安裝](assets/batch-install.jpg)

ZIP 咖啡版：為了感謝 Buy me a coffee的朋友，所以這個版本不只有底層靈魂可以注入，還可以有多個靈魂可以自行定義後選擇注入，直接下載點擊setup_win.bat就可以安裝到好

👉下載連結：
[嘴炮輸入法 免費版 Mac Version](https://portaly.cc/jimmy4tw/product/AcZCAt5kVqhnmLFYCYIY) | [嘴炮輸入法 咖啡版 Mac Version](https://portaly.cc/jimmy4tw/product/9lXTA2fYnspWugYuUvAL)
| [嘴炮輸入法 咖啡版 Windows Version](https://hi.jimmy4.tw/product/Ow5uKOdcHzgsyxMc8XE6)

---

![影片縮圖](assets/youtube-cover.jpg)

👉 [點我觀看完整影片](https://www.youtube.com/watch?v=gZA-GSiRJqw)


---

## 為什麼做這套工具

![Dashboard](assets/screenshot-pc-01.jpg)

靈感來自TypeLess這類語音輸入工具，但因為授權限制與雲端依賴，我就想：能不能做一套「完全可以在本地端自己掌握」的語音輸入工具  
於是就結合Apple Silicon的本地Whisper能力，再加上Gemini、Nebula等AI夥伴，一起打造出這套專為Mac打造的VoiceType4TW，也就是嘴炮輸入法

---

![辨識AI](assets/screenshot-pc-02.jpg)

## 功能特色

- **Windows 深度優化**：專為 Windows 10/11 打造——一鍵安裝（自動下載可攜式 Python、偵測 NVIDIA GPU 條件安裝 CUDA）、原生 Starter EXE 啟動免黑窗。
- **全域快捷鍵**：按住說話 (PTT) 或 切換開關 (Toggle)，反應迅速不卡頓。
- **🎤 全時模式**：免按鍵自動觸發——VAD 偵測語音自動切句辨識，說完就輸出。
- **📍 位置記憶**：錄音指示器與浮動按鈕可拖曳，記住你在每個螢幕的偏好停靠位置。
- **神經級辨識**：搭載本地 Faster-Whisper，支援各平台硬體加速。
- **✨ 多螢幕跟隨**：Indicator 會自動偵測滑鼠位置並出現在對應螢幕。
- **🔵 完成感官優化**：貼回文字時觸發亮藍色閃爍與音效 (可於設定關閉)。
- **✨ 三層式靈魂系統**：結合「基底靈魂 + 情境模板 + 格式決定」，打造個人化 AI 風格。
- **⚡️ 旗艦預設情境**：隨附商務英文、專業回應、社群貼文、情商大師等優質人格。
- **Instant Translation 魔術語**：用語音即時切換翻譯模式，無需動手操作設定。
- **不搶焦點設計**：深度優化視窗屬性，確保文字直接精準注入當前編輯位置。
- **智慧詞彙學習**：自動記憶專有名詞與常用關鍵字。

---

## 浮動錄音狀態視窗

![浮動錄音狀態視窗](assets/screenshot-miclevel.jpg)

這裡有多種模式呈現

- 左側沒有AI的字樣，直接辨識、輸出
- 左側有AI的部分，透過LLM做修飾完成之後再輸出
- 黃色模式，當我們的語音講完之後，它就開始做辨識
- 翻譯成英文，當你直接講中文，它就會翻譯成英文
- 翻譯成日文，當你直接講中文，它就會翻譯成日文


---

## ✨ 靈魂治理：三層疊加系統

![靈魂治理](assets/screenshot-pc-03.jpg)

這套系統最核心的特色在於您可以自由調配 AI 的「靈魂組成」：

1.  **🏠 基底靈魂 (Base)**：定義 AI 的核心價值觀，例如：不廢話、修正錯字、繁體中文輸出。
2.  **🎭 情境模板 (Scenario)**：定義特定場合的對話風格，如：`💼 商務回應`、`🌐 商務英文`、`📱 社群貼文`。
3.  **📝 輸出格式 (Format)**：決定最後呈現的樣子，例如：電子郵件格式、條列式筆記、Markdown 表格。

透過 Menu Bar 可以隨時組合不同靈魂，讓輸入法真正成為您的私人助理。

---

## 詞彙記憶

![詞彙記憶](assets/screenshot-pc-04.jpg)

因為吉米常常需要輸入一些專有名詞，或者是客戶的品牌名稱，所以我在這個地方設計了一個詞彙新增的功能，可以手動輸入我們想要辨識的專有名詞

甚至我這邊是設定了，當一個詞彙出現三次以上，他會自動把它記錄起來

因為有了「養龍蝦」觀念的經驗之後，我也希望它能夠擁有一個長期記錄

每一週，它會去把當週所有的記憶做一個濃縮之後再另存起來，讓它持續保有我們之前所有的記憶

我的想法是這樣子啦


---

![翻譯功能](assets/screenshot-menubar.jpg)

## 連同靈魂情境一起翻譯

我設定了翻成英文、翻成日文與恢復原狀等三個選項

這些翻譯可以疊加在上面靈魂注入後的結果，所以可以選擇扮演哪個靈魂，然後用什麼語言輸出



![雲端同步](assets/screenshot-pc-07.jpg)

## 自定同步資料夾

因為我常常需要在Mac跟PC的之間切換，所以我希望我的記憶跟常用的這些詞彙可以共用，因此我設計了雲端目錄夾同步的一個概念。

只要你把它設定在你的同步的目錄，不管你是用iCloud、是用Google Drive、是用NAS來做同步都可以。

---

## 數據統計

![數據統計](assets/screenshot-pc-05.jpg)

這套系統會記錄你輸入了多少語音，語音總長度是多少，然後再除以一般人平均每分鐘的打字字數，總結出幫你省下多少時間的統計。

希望讓大家長久使用下來，能夠看到一個漂亮的數據！

---

## 系統設定

![系統設定](assets/screenshot-pc-06.jpg)

設定成要按哪個按鈕來觸發語音輸入法的設定頁面。在這個地方可以設定按住錄音 (PTT) 或 單擊開關 (Toggle) 的運作方式。

結果自動貼上，這玩意兒就是會把我們輸入之後的文字，自動貼上我們所在Focus的視窗輸入頁面上面，同時也會存在剪貼簿裡面。

如果說它沒有出現的話，你只要直接按Ctrl-V貼上就可以了。

然後，如果你是喜歡看這個輸出結果的話，你可以啟用詳細一日制輸出，這個只有在Terminal的視窗上面會出現，這是我們在Debug的時候使用的。


---

## 工作流程

1. 按下你設定好的快捷鍵開始講話  
2. 系統透過本地Whisper或Groq雲端進行語音辨識  
3. 可選擇直接輸出文字，或先丟給LLM做潤飾、整理口氣、調整風格  
4. 輸出結果自動送回目前有輸入焦點的應用程式  
5. 若使用魔術語，則會在流程中自動進行翻譯後再輸出  

---

### Windows 安裝 (ZIP 咖啡版)

![批次安裝](assets/batch-install.jpg)

👉下載連結：
[嘴炮輸入法 免費版 Mac Version](https://portaly.cc/jimmy4tw/product/AcZCAt5kVqhnmLFYCYIY) | [嘴炮輸入法 咖啡版 Mac Version](https://portaly.cc/jimmy4tw/product/9lXTA2fYnspWugYuUvAL)
[嘴炮輸入法 咖啡版 Windows Version](https://hi.jimmy4.tw/product/Ow5uKOdcHzgsyxMc8XE6)

ZIP安裝版下載後，解壓縮到你想要放置的位置，記得不要放在要求系統管理員權限的目錄下面（或是你手動給權限）

安裝所需軟體與模型，點擊 setup_win.bat

安裝完成之後，桌面點擊「嘴炮輸入法」執行

或是安裝目錄下執行
run_voicetype4tw.bat


## 🛠️ 安裝失敗排除 (BAT 腳本報錯)

若執行 `setup_win.bat` 時卡在「建立虛擬環境 (venv)」或「安裝依賴」階段，通常與 **磁碟寫入權限** 有關。

### ❌ 常見錯誤成因：安裝在 C 槽受保護目錄
- 安裝路徑在 `C:\` 根目錄。
- 安裝路徑在 `C:\Program Files` 或 `C:\Program Files (x86)`。
- Windows 系統會限制未授權腳本在這些位置寫入大量小檔案。

### ✅ 解決方案：
1. **更換安裝路徑 (推薦)**：
   將整個 `voicetype4tw-mac` 資料夾移至 **D 槽**、**E 槽** 或其他非系統磁碟區。
   *例如：`D:\Tools\VoiceType4TW`*

2. **移動至用戶資料夾**：
   如果只有 C 槽，請放在 `C:\Users\<您的名稱>\Documents` 或 `桌面` 執行。

3. **以系統管理員身分執行**：
   對 `setup_win.bat` 按 **右鍵** -> 選擇 **「以系統管理員身分執行」**。

---

## 打包真可攜版（開發者）

要製作「解壓即用」的可攜 ZIP（免裝 Python、離線可用、隨身碟可帶著走）：

```powershell
.\release_win.ps1          # Full：含 CUDA 加速 + medium 模型（約 4GB）
.\release_win.ps1 -Lite    # Lite：無 CUDA 無模型，首次啟動線上下載（約 300MB）
```

產出在 `dist\VoiceType4TW_Win_Portable_V****.zip`，對方解壓後雙擊 `VoiceType4TW.exe` 即可使用。

## 手動安裝

如果你想自己來，也可以手動操作（需 Python 3.10–3.12）：

```bat
rem 1. Clone 本專案（Windows 專用版，win-stable 分支）
git clone -b win-stable https://github.com/go-mask/voicetype4tw-mac.git
cd voicetype4tw-mac

rem 2. 建立虛擬環境
py -3.12 -m venv venv
venv\Scripts\activate

rem 3. 安裝依賴（有 NVIDIA GPU 才需要第二行）
pip install -r requirements-win.txt
pip install -r requirements-cuda-win.txt

rem 4. 啟動
python main.py
```


---

## 設定

設定檔位於 `%APPDATA%\VoiceType4TW\`（`config_local.json` 為本機設定、`config_global.json` 參與雲端同步），大多數選項都可以直接在應用程式的設定視窗調整：

| 欄位                       | 說明                                                    | 預設值          |
|----------------------------|---------------------------------------------------------|-----------------|
| `hotkey_ptt`               | 按住說話快捷鍵 (alt_r / ctrl_r / shift_r / f13-f15 / code:VK) | `alt_r`     |
| `hotkey_toggle`            | 切換開關快捷鍵                                          | `f13`           |
| `auto_trigger_enabled`     | 🎤 全時模式（免按鍵自動觸發）                            | `false`         |
| `auto_trigger_sensitivity` | 全時模式觸發門檻 (0~1，越高越不敏感)                     | `0.15`          |
| `auto_trigger_silence_sec` | 全時模式靜音幾秒視為一句結束                             | `1.5`           |
| `stt_engine`               | 語音引擎 (local_whisper / groq / gemini / openrouter)   | `local_whisper` |
| `whisper_model`            | Whisper模型大小 (tiny/base/small/medium/large)          | `medium`        |
| `groq_api_key`             | Groq API Key (使用groq引擎時填入)                       | `""`            |
| `llm_enabled`              | 是否啟用AI文字潤飾                                      | `false`         |
| `llm_engine`               | LLM引擎 (ollama / openai / claude / openrouter / gemini / deepseek / qwen) | `ollama` |
| `language`                 | 辨識語言                                                | `zh`            |

---

## 系統需求

- **Windows** 10/11（Python 3.10–3.12；沒裝 Python 也沒關係，`setup_win.bat` 會自動下載可攜式 Python 3.12，不需要系統管理員權限）。
- **顯示卡**：有 NVIDIA GPU 會自動安裝 CUDA 加速函式庫；沒有的話會自動改用 CPU 模式（省下約 800MB 下載量）。
- **記憶體**: 建議 16GB 以上。

---

## 支援與回饋


如果你覺得嘴炮輸入法對你有幫助，歡迎：

- 在GitHub按顆星支持  
- 分享給身邊常需要打字、開會做紀錄、寫文件的朋友  
- [請吉米喝杯咖啡、小額贊助，支持持續開發](https://hi.jimmy4.tw/support)

有任何功能建議、或想一起共創的點子，都可以：

- 直接在GitHub開Issue  
- 透過吉米的SNS管道來找我聊聊  
