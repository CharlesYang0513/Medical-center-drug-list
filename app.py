# -*- coding: utf-8 -*-
"""
醫學中心藥品查詢 — Streamlit 網頁

輸入藥品名稱或成分，一次查詢多家醫學中心院內用藥清單是否收載該藥品，
結果彙整列表於頁面下方，並可下載為 Excel。

執行方式（本機）：
    pip install -r requirements.txt
    playwright install chromium
    streamlit run app.py

部署到 Streamlit Community Cloud 時，本檔案開頭會自動執行
`playwright install chromium`（見 _ensure_playwright_browser），
不需要額外手動下指令，但仍需搭配 packages.txt 安裝系統層級依賴。

重要說明：
    本工具對於需要圖形驗證碼的醫院查詢頁面（台北榮總、新光醫院）
    「不會」嘗試自動辨識或略過驗證碼，一律標記為「需人工查詢」並提供
    直接連結，請使用者自行開啟該醫院網站輸入驗證碼查詢。
"""

import subprocess
import sys
import time
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="醫學中心藥品查詢", layout="wide")


@st.cache_resource(show_spinner="首次啟動：正在安裝瀏覽器引擎（僅第一次執行需要，約1-2分鐘）...")
def _ensure_playwright_browser():
    """部署在 Streamlit Community Cloud 時，容器內不會預先裝好 Chromium，
    這裡在整個 app 生命週期中只執行一次 `playwright install chromium`。
    本機執行若已手動跑過 `playwright install chromium`，這裡會很快跳過。"""
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=False,
    )
    return True


_ensure_playwright_browser()

from playwright.sync_api import sync_playwright  # noqa: E402  (需在安裝完成後才 import 使用)
from hospitals import HOSPITALS, HOSPITAL_BY_KEY  # noqa: E402

st.title("醫學中心藥品查詢")
st.caption("輸入藥品名稱／成分，查詢各醫學中心院內用藥清單是否收載。")

with st.sidebar:
    st.header("查詢設定")
    query = st.text_input("藥品名稱或成分（建議使用英文學名）", value="")
    st.markdown("**選擇要查詢的醫院**")
    select_all = st.checkbox("全選", value=True)
    chosen = []
    for h in HOSPITALS:
        badge = {"auto": "✅", "auto_best": "🟡", "manual": "🔒"}[h.mode]
        default = select_all
        checked = st.checkbox(f"{badge} {h.name}", value=default, key=f"chk_{h.key}")
        if checked:
            chosen.append(h.key)
    st.markdown("---")
    st.caption("✅ 今日已實測　🟡 選取器未完整驗證　🔒 需人工輸入驗證碼（不自動處理）")
    run = st.button("開始查詢", type="primary", use_container_width=True)

if "results" not in st.session_state:
    st.session_state["results"] = None


def run_query(query: str, hospital_keys: list[str]):
    rows = []
    progress = st.progress(0.0, text="準備開始查詢...")
    total = len(hospital_keys)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        for i, key in enumerate(hospital_keys):
            h = HOSPITAL_BY_KEY[key]
            progress.progress((i) / max(total, 1), text=f"查詢中：{h.name}")

            if h.mode == "manual":
                rows.append({
                    "醫院名稱": h.name,
                    "藥品名稱（原文）": query,
                    "查詢結果": "需人工查詢",
                    "備註": f"{h.note}｜連結：{h.url}",
                    "查詢時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                continue

            page = context.new_page()
            try:
                result = h.scrape(page, query)
                rows.append({
                    "醫院名稱": h.name,
                    "藥品名稱（原文）": query,
                    "查詢結果": result["status"],
                    "備註": (h.note + "｜" if h.note else "") + (
                        "" if result["status"] == "有收載" else "詳見原始頁面文字（可展開查看）"
                    ),
                    "查詢時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "_raw": result.get("raw", ""),
                })
            except Exception as e:
                rows.append({
                    "醫院名稱": h.name,
                    "藥品名稱（原文）": query,
                    "查詢結果": "查詢失敗",
                    "備註": f"自動化發生錯誤：{e}｜可改至連結人工查詢：{h.url}",
                    "查詢時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
            finally:
                page.close()

        browser.close()
    progress.progress(1.0, text="查詢完成")
    time.sleep(0.3)
    progress.empty()
    return rows


if run:
    if not query.strip():
        st.warning("請先輸入藥品名稱或成分。")
    elif not chosen:
        st.warning("請至少選擇一家醫院。")
    else:
        st.session_state["results"] = run_query(query.strip(), chosen)

results = st.session_state["results"]

if results:
    st.subheader("查詢結果")
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "_raw"} for r in results])

    def _color(val):
        if val == "有收載":
            return "background-color:#d4edda"
        if val == "未收載":
            return "background-color:#f8d7da"
        if val == "需人工查詢":
            return "background-color:#fff3cd"
        if val == "查詢失敗":
            return "background-color:#e2e3e5"
        return ""

    st.dataframe(
        df.style.map(_color, subset=["查詢結果"]),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("查看各醫院原始查詢頁面文字（除錯用）"):
        for r in results:
            if r.get("_raw"):
                st.markdown(f"**{r['醫院名稱']}**")
                st.text(r["_raw"][:2000])
                st.markdown("---")

    excel_path = "/tmp/drug_query_result.xlsx"
    df.to_excel(excel_path, index=False)
    with open(excel_path, "rb") as f:
        st.download_button(
            "下載 Excel 彙整表",
            data=f,
            file_name=f"{query}_醫院查詢結果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("請在左側輸入藥品名稱、選擇醫院後按「開始查詢」。")
