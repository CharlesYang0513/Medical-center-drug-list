# -*- coding: utf-8 -*-
"""
13 家醫學中心藥品查詢設定與爬取邏輯。

自動化程度分三種：
  - "auto"        今天已用真實瀏覽器實測過選取器，可信度較高
  - "auto_best"   尚未實測，依資料卡描述推測選取器，可能需要微調
  - "manual"      頁面需要圖形驗證碼，本工具不會嘗試辨識/略過驗證碼
                  （辨識與略過驗證碼一律排除在自動化範圍之外），
                  僅提供直接連結，請使用者自行至醫院網站輸入驗證碼查詢

重要：本程式「不會」對任何頁面進行驗證碼辨識或繞過。遇到驗證碼一律
標記為 manual，交由使用者自己完成查詢。
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
from playwright.sync_api import Page


@dataclass
class Hospital:
    key: str
    name: str
    url: str
    mode: str  # "auto" | "auto_best" | "manual"
    note: str = ""
    scrape: Optional[Callable[[Page, str], dict]] = None


def _no_data_text(text: str) -> bool:
    markers = ["查無資料", "查無此藥", "共 0 筆", "0 筆資料", "無符合", "找不到"]
    return any(m in text for m in markers)


# ---------- 個別醫院爬取函式（今日已實測者，選取器較準確）----------

def scrape_cmuh(page: Page, query: str) -> dict:
    """中國醫藥大學附設醫院"""
    page.goto("https://druginfo.cmuh.org.tw/DrugNetNew/BookInfo/DrugQuery.aspx", timeout=60000)
    page.wait_for_load_state("networkidle")
    box = page.locator("input[type=text]").first
    box.fill(query)
    page.get_by_role("button", name="查詢").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_cch(page: Page, query: str) -> dict:
    """彰化基督教醫院"""
    page.goto("https://www.cch.org.tw/drug.aspx", timeout=60000)
    page.wait_for_load_state("networkidle")
    box = page.get_by_placeholder("請輸入藥品之學名、商品名、俗名...等關鍵字")
    box.scroll_into_view_if_needed()
    box.fill(query)
    page.locator("text=查詢").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text) or "藥品辨識系統" not in text:
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_cgh(page: Page, query: str) -> dict:
    """國泰綜合醫院 —— 注意：此站 robots.txt 對查詢路徑有限制，
    僅在使用者主動單次查詢時才個別請求，不做批次/高頻爬取。"""
    page.goto(
        "https://med.cgh.org.tw/unit/branch/Pharmacy/pharm/webidentify-cgh.asp",
        timeout=60000,
    )
    box = page.locator("input[type=text]").first
    box.fill(query)
    page.locator("input[type=button][value='查詢'], input[value='查詢']").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text) or "學名" not in text:
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_vghtc(page: Page, query: str) -> dict:
    """台中榮民總醫院"""
    page.goto("https://www3.vghtc.gov.tw:8443/pharmacyHandbook/#/handbook/search", timeout=60000)
    page.wait_for_load_state("networkidle")
    box = page.get_by_placeholder("藥品查詢關鍵字")
    box.fill(query)
    page.get_by_role("button", name="查詢").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if "共查詢到 0 筆" in text or _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_vghks(page: Page, query: str) -> dict:
    """高雄榮民總醫院"""
    page.goto("https://www2.vghks.gov.tw/DIWEB/DIQuery.jsp?value(hid)=1A0", timeout=60000)
    box = page.locator("input[type=text]").first
    box.fill(query)
    page.locator("input[type=button]").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if "健保碼" not in text or _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_vghtpe(page: Page, query: str) -> dict:
    """台北榮民總醫院 —— 需圖形驗證碼，manual only（不會被呼叫到）"""
    raise NotImplementedError("此醫院需人工輸入驗證碼，不進行自動查詢")


def scrape_skh(page: Page, query: str) -> dict:
    """新光醫院 —— 依藥名查詢一律要求圖形驗證碼，manual only（不會被呼叫到）"""
    raise NotImplementedError("此醫院查詢需人工輸入驗證碼，不進行自動查詢")


# ---------- 尚未於今日實測，依資料卡描述推測（auto_best，可能需微調）----------

def scrape_ntuh(page: Page, query: str) -> dict:
    page.goto("https://reg.ntuh.gov.tw/pharmacyoutside/QueryDrug.aspx", timeout=60000)
    page.wait_for_timeout(6000)  # 頁面需等待 JS 完全載入，雲端環境網路較慢，拉長等待
    box = page.get_by_placeholder("").nth(1) if False else page.locator("input[type=text]").nth(1)
    box.fill(query)
    page.locator("input[type=submit], button").nth(1).click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_cgmh(page: Page, query: str) -> dict:
    page.goto("https://www.cgmh.org.tw/tw/Services/Drug", timeout=60000)
    page.wait_for_load_state("networkidle")
    box = page.get_by_placeholder("請輸入關鍵字或條碼")
    box.fill(query)
    page.get_by_role("button", name="確認送出").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_mmh(page: Page, query: str) -> dict:
    page.goto("https://mcloud.mmh.org.tw/DMZDrugFormB817/DrugQuery.html", timeout=60000)
    box = page.locator("input[type=text]").first
    box.fill(query)
    page.get_by_role("button", name="查詢Search").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_femh(page: Page, query: str) -> dict:
    page.goto("https://www.e-pharm.info/safety/drug-information/femh-formulary", timeout=60000)
    page.wait_for_load_state("networkidle")
    box = page.get_by_placeholder("英文成分") if False else page.locator("input[type=text], input[type=search]").first
    box.fill(query)
    page.get_by_role("button", name="搜尋").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_chimei(page: Page, query: str) -> dict:
    page.goto("https://www.chimei.org.tw/MedQuery/search", timeout=60000)
    page.wait_for_load_state("networkidle")
    box = page.locator("input[type=text], input[type=search]").first
    box.fill(query)
    page.get_by_role("button", name="查詢").first.click()
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


def scrape_ncku(page: Page, query: str) -> dict:
    """成大醫院 —— 頁面待確認，先嘗試自動化，失敗則請人工查詢"""
    page.goto("https://web.hosp.ncku.edu.tw/pharmacy/", timeout=60000)
    page.wait_for_load_state("networkidle")
    box = page.locator("input[type=text], input[type=search]").first
    box.fill(query)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    if _no_data_text(text):
        return {"status": "未收載", "raw": text}
    return {"status": "有收載", "raw": text}


HOSPITALS = [
    Hospital("ntuh", "台大醫院", "https://reg.ntuh.gov.tw/pharmacyoutside/QueryDrug.aspx",
             "auto_best", "選取器尚未完整驗證，建議先小量測試", scrape_ntuh),
    Hospital("vghtpe", "台北榮總", "https://www7.vghtpe.gov.tw/home/index",
             "manual", "頁面有圖形驗證碼，本工具不辨識驗證碼，請自行查詢", None),
    Hospital("cgmh", "林口長庚", "https://www.cgmh.org.tw/tw/Services/Drug",
             "auto_best", "選取器尚未完整驗證，建議先小量測試", scrape_cgmh),
    Hospital("vghtc", "台中榮總", "https://www3.vghtc.gov.tw:8443/pharmacyHandbook/#/handbook/search",
             "auto", "今日已實測", scrape_vghtc),
    Hospital("ncku", "成大醫院", "https://web.hosp.ncku.edu.tw/pharmacy/",
             "auto_best", "頁面結構待確認，若自動失敗請人工查詢", scrape_ncku),
    Hospital("vghks", "高雄榮總", "https://www2.vghks.gov.tw/DIWEB/DIQuery.jsp?value(hid)=1A0",
             "auto", "今日已實測", scrape_vghks),
    Hospital("mmh", "馬偕醫院", "https://mcloud.mmh.org.tw/DMZDrugFormB817/DrugQuery.html",
             "auto_best", "靜態表單，成功率預期較高", scrape_mmh),
    Hospital("skh", "新光醫院", "https://www.skh.org.tw/skh_regis/#/register/drug",
             "manual", "「依藥名查詢」頁籤仍要求圖形驗證碼，本工具不辨識驗證碼，請自行查詢", None),
    Hospital("femh", "亞東醫院", "https://www.e-pharm.info/safety/drug-information/femh-formulary",
             "auto_best", "選取器尚未完整驗證，建議先小量測試", scrape_femh),
    Hospital("chimei", "奇美醫院", "https://www.chimei.org.tw/MedQuery/search",
             "auto_best", "選取器尚未完整驗證，建議先小量測試", scrape_chimei),
    Hospital("cgh", "國泰醫院", "https://med.cgh.org.tw/unit/branch/Pharmacy/pharm/webidentify-cgh.asp",
             "auto", "今日已實測；⚠ 該站 robots.txt 限制自動爬取，僅建議單次人工觸發查詢使用", scrape_cgh),
    Hospital("cch", "彰基", "https://www.cch.org.tw/drug.aspx",
             "auto", "今日已實測（未特別選擇院區，採用院方預設頁面）", scrape_cch),
    Hospital("cmuh", "中國附醫", "https://druginfo.cmuh.org.tw/DrugNetNew/BookInfo/DrugQuery.aspx",
             "auto", "今日已實測", scrape_cmuh),
]

HOSPITAL_BY_KEY = {h.key: h for h in HOSPITALS}
