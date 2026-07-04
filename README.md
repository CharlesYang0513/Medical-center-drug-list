# 醫學中心藥品查詢（Streamlit）

輸入藥品名稱或成分，一次查詢多家醫學中心院內用藥清單是否收載。

## 安裝與執行（本機）

```bash
cd drug_query_app
pip install -r requirements.txt
playwright install chromium
streamlit run app.py
```

瀏覽器會自動開啟 `http://localhost:8501`。

## 部署到 Streamlit Community Cloud（像 NHIA-item 那樣，用網址直接開）

Streamlit Community Cloud（share.streamlit.io）不支援直接把 .py 檔案拖進網站，
一定要先放進 GitHub repo，再用 GitHub 帳號連結部署。步驟如下：

1. **申請 GitHub 帳號**（若還沒有）：到 github.com 註冊。
2. **建立一個新 repository**：右上角 `+` → `New repository`，Public（免費方案
   只能部署 public repo），例如命名 `drug-query-app`。
3. **把這個資料夾的檔案上傳上去**：進入剛建立的 repo 頁面，點
   `Add file` → `Upload files`，把 `app.py`、`hospitals.py`、
   `requirements.txt`、`packages.txt` 這四個檔案拖進去，按 `Commit changes`。
   （不需要用 git 指令，網頁拖拉上傳即可）
4. **到 share.streamlit.io 部署**：用剛剛的 GitHub 帳號登入 → `New app` →
   選擇你的 repo、branch（通常是 `main`）、Main file path 填 `app.py` →
   按 `Deploy`。
5. 第一次啟動會比較慢（因為程式碼裡會自動執行
   `playwright install chromium` 下載瀏覽器引擎，見 `app.py` 開頭的
   `_ensure_playwright_browser()`），耐心等 1-2 分鐘。
6. 部署成功後會拿到一個固定網址，例如
   `https://drug-query-app-xxxx.streamlit.app`，之後直接分享這個網址就能用，
   不用再叫我或你自己重新部署。

### `packages.txt` 是什麼？

Streamlit Cloud 的容器預設沒有 Playwright/Chromium 需要的系統層級函式庫
（例如 `libnss3`），`packages.txt` 就是告訴 Streamlit Cloud 要用 `apt-get`
額外安裝哪些套件，這個檔案已經幫你準備好，直接上傳到 GitHub 一起部署即可，
不需要修改。

### 已知的雲端部署眉角（含 2026-07-04 實際部署踩過的坑）

* **`libcups2` 與 `libcups2t64` 衝突**：Streamlit Cloud 目前的 Debian 基底
  （trixie）把 `libcups2` 改名為 `libcups2t64`，若 `packages.txt` 同時列出
  舊名 `libcups2`，會跟 `libgtk-3-0` 間接拉進來的新名衝突，導致
  apt-get 直接失敗。**解法：`packages.txt` 不要列 `libcups2`**（新名會透過
  `libgtk-3-0` 自動裝好），本專案的 `packages.txt` 已經修正。
* **`playwright` 版本不要釘死**：曾嘗試把版本鎖在 `1.49.0`（社群早期建議），
  結果在 Streamlit Cloud 目前的 Python 版本上，舊版 `playwright` 依賴的
  `greenlet` 沒有現成的安裝檔（wheel），需要從原始碼編譯又失敗
  （`Failed building wheel for greenlet`）。**解法：`requirements.txt`
  改成不鎖版本的 `playwright`**，讓 pip 自動抓最新版（新版的 greenlet
  依賴有對應目前 Python 版本的 wheel），本專案已經改成不鎖版本。
* 如果之後 Streamlit Cloud 又更新底層映像檔，上述兩個問題都可能再變化，
  遇到新的安裝錯誤，把「Manage app」裡的完整終端機錯誤訊息貼出來，才能
  準確定位是哪個套件、哪個版本的問題。
* 國泰醫院那頁的 `robots.txt` 對查詢路徑有限制——公開部署後任何人都
  能觸發查詢，等於變成不特定使用者的重複請求，如果之後發現國泰醫院那
  格經常失敗或被擋，可以考慮把 `hospitals.py` 裡 `cgh` 這家的 `mode`
  改成 `"manual"`，退回連結手動查詢即可。
* 這個 app 目前沒有帳號限制，repo 是 public 的話任何人都能看到程式碼、
  任何知道網址的人都能用；如果你想限制存取，Streamlit Cloud 付費方案
  才有私有 repo／存取控制的選項。

## 醫院自動化狀態

| 標記 | 意義 |
|---|---|
| ✅ | 2026-07-04 已用真實瀏覽器實測選取器可正常運作 |
| 🟡 | 依醫院查詢頁面描述推測選取器，尚未實測，可能需要微調 |
| 🔒 | 頁面查詢需輸入圖形驗證碼，本工具**不會**辨識或略過驗證碼，僅提供連結供人工查詢 |

已實測（✅）：台大醫院、台中榮總、高雄榮總、國泰醫院、彰基、中國附醫、
林口長庚、馬偕醫院、亞東醫院、奇美醫院（2026-07-04 依使用者提供的實際
查詢截圖逐一核對欄位與結果）
需人工查詢（🔒）：台北榮總、新光醫院（「依藥名查詢」頁籤仍強制要求驗證碼）
尚待完全驗證（🟡）：成大醫院（頁面另有圖形驗證碼欄位，本工具不會填寫；
目前觀察到不填也能查到結果，但不保證長期穩定）

## 為什麼不自動處理驗證碼？

自動辨識或繞過驗證碼（CAPTCHA）不在本工具的功能範圍內。遇到強制驗證碼
的醫院，程式會直接標記「需人工查詢」並附上該院查詢頁連結，請自行開啟
網頁、輸入驗證碼查詢。

## 已知限制

* 🟡 標記的醫院選取器僅依資料卡描述推測，首次使用建議先用已知藥品（如
  `bisoprolol`）測試比對正確性，如有落差請依實際頁面調整
  `hospitals.py` 中對應的 `scrape_*` 函式。
* 國泰醫院查詢頁面的 `robots.txt` 對該路徑有限制，本工具僅在使用者
  主動按下查詢時才個別發出請求，請避免寫成排程或批次高頻呼叫。
* 部分醫院為 JS 單頁應用（SPA），已使用 Playwright 等待網路閒置
  （`networkidle`）再操作，若查詢逾時可自行增加 `page.wait_for_timeout`
  的等待秒數。
* 本沙盒環境無法連線至醫院網域，因此程式邏輯未能在此環境完整跑過
  端對端連線測試，請在你自己的電腦上安裝執行後測試。
