"""
네이버/구글 검색 자동화 앱
사용법:
  pip3 install selenium webdriver-manager
  python3 search_bot.py
"""

import os
import warnings
os.environ['TK_SILENCE_DEPRECATION'] = '1'
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

import datetime
import queue
import random
import threading
import tkinter as tk
from tkinter import messagebox
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

NAVER_URL = "https://search.naver.com/search.naver?query={}"
GOOGLE_URL = "https://www.google.com/search?q={}"
SEARCH_COUNT = 50

BG      = "#ffffff"
FG      = "#111111"
FG2     = "#555555"
ENTRY   = "#f2f2f2"
SEP     = "#dddddd"


class SearchBot:
    def __init__(self, keywords: list[str], log_fn, stop_event: threading.Event):
        self.keywords = keywords
        self.log = log_fn
        self.stop_event = stop_event

    def _make_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        options.add_argument("--window-size=1024,768")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

    def _random_delay(self, min_s: float, max_s: float):
        elapsed = 0.0
        target = random.uniform(min_s, max_s)
        interval = 0.2
        while elapsed < target:
            if self.stop_event.is_set():
                return
            wait = min(interval, target - elapsed)
            self.stop_event.wait(timeout=wait)
            elapsed += wait

    def _search_site(self, driver: webdriver.Chrome, url_template: str,
                     keyword: str, site_name: str):
        encoded = quote_plus(keyword)
        url = url_template.format(encoded)
        for i in range(1, SEARCH_COUNT + 1):
            if self.stop_event.is_set():
                return
            try:
                driver.get(url)
            except Exception as e:
                self.log(f"[오류] {site_name} | {keyword} | {i}/{SEARCH_COUNT}: {e}")
            self.log(f"{site_name} | {keyword} | {i}/{SEARCH_COUNT} 완료")
            if i % 10 == 0 and i < SEARCH_COUNT:
                self.log("  → 10회 단위 추가 대기 중...")
                self._random_delay(15.0, 30.0)
            else:
                self._random_delay(3.0, 7.0)

    def run(self):
        driver = None
        try:
            self.log("Chrome 브라우저 시작 중...")
            driver = self._make_driver()
            for keyword in self.keywords:
                if self.stop_event.is_set():
                    break
                self.log(f"\n[검색어: {keyword}] 네이버 검색 시작")
                self._search_site(driver, NAVER_URL, keyword, "네이버")
                if self.stop_event.is_set():
                    break
                self.log("  → 사이트 전환 대기 중...")
                self._random_delay(10.0, 20.0)
                if self.stop_event.is_set():
                    break
                self.log(f"[검색어: {keyword}] 구글 검색 시작")
                self._search_site(driver, GOOGLE_URL, keyword, "구글")
                if self.stop_event.is_set():
                    break
                self.log(f"[검색어: {keyword}] 완료\n")
        except Exception as e:
            self.log(f"[오류] {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            if self.stop_event.is_set():
                self.log("검색이 중지되었습니다.")
            else:
                self.log("모든 검색이 완료되었습니다.")


class SearchApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.configure(bg=BG)
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self._polling = False
        self._build_ui()

    def _label(self, parent, text, font=None, fg=FG, anchor="w", **kw):
        return tk.Label(parent, text=text, bg=BG, fg=fg,
                        font=font or ("Helvetica", 12),
                        anchor=anchor, **kw)

    def _sep(self, parent):
        tk.Frame(parent, bg=SEP, height=1).pack(fill="x", padx=14, pady=8)

    def _build_ui(self):
        self.root.title("네이버/구글 검색 자동화")
        self.root.geometry("500x570")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 제목
        self._label(self.root, "네이버 / 구글 검색 자동화",
                    font=("Helvetica", 16, "bold"),
                    anchor="center").pack(pady=(20, 4), fill="x")
        self._sep(self.root)

        # 검색어
        self._label(self.root, "검색어",
                    font=("Helvetica", 11, "bold"),
                    fg=FG2).pack(fill="x", padx=16)

        self.keyword_entries: list[tk.Entry] = []
        for i in range(1, 4):
            row = tk.Frame(self.root, bg=BG)
            row.pack(fill="x", padx=16, pady=4)
            self._label(row, f"검색어 {i}:", width=8).pack(side="left")
            e = tk.Entry(row, width=36, bg=ENTRY, fg=FG,
                         insertbackground=FG, relief="solid",
                         bd=1, font=("Helvetica", 13))
            e.pack(side="left", padx=6, ipady=4)
            self.keyword_entries.append(e)

        self._sep(self.root)

        # 실행 시간
        self._label(self.root, "실행 시간",
                    font=("Helvetica", 11, "bold"),
                    fg=FG2).pack(fill="x", padx=16)

        time_row = tk.Frame(self.root, bg=BG)
        time_row.pack(padx=16, pady=8)

        now = datetime.datetime.now()
        self.hour_var = tk.StringVar(value=str(now.hour))
        default_m = (now.minute // 5) * 5
        self.minute_var = tk.StringVar(value=str(default_m))

        hours   = [str(h) for h in range(24)]
        minutes = [str(m) for m in range(0, 60, 5)]

        self._label(time_row, "시각:").pack(side="left")
        for var, vals, unit in [
            (self.hour_var, hours, "시"),
            (self.minute_var, minutes, "분"),
        ]:
            om = tk.OptionMenu(time_row, var, *vals)
            om.configure(bg=ENTRY, fg=FG, activebackground="#e0e0e0",
                         activeforeground=FG, relief="solid",
                         bd=1, width=4, highlightthickness=0,
                         font=("Helvetica", 12))
            om["menu"].configure(bg=ENTRY, fg=FG, font=("Helvetica", 12))
            om.pack(side="left", padx=6)
            self._label(time_row, unit).pack(side="left")

        self._sep(self.root)

        # 버튼
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=4)

        self.start_btn = tk.Button(
            btn_frame, text="  시  작  ", width=10,
            bg="#4CAF50", fg="white",
            activebackground="#388E3C", activeforeground="white",
            font=("Helvetica", 12, "bold"), relief="flat",
            command=self._on_start)
        self.start_btn.pack(side="left", padx=16)

        self.stop_btn = tk.Button(
            btn_frame, text="  중  지  ", width=10,
            bg="#e53935", fg="white",
            activebackground="#b71c1c", activeforeground="white",
            font=("Helvetica", 12, "bold"), relief="flat",
            state="disabled",
            command=self._on_stop)
        self.stop_btn.pack(side="left", padx=16)

        self._sep(self.root)

        # 로그
        self._label(self.root, "로그",
                    font=("Helvetica", 11, "bold"),
                    fg=FG2).pack(fill="x", padx=16)

        log_frame = tk.Frame(self.root, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        scrollbar = tk.Scrollbar(log_frame, bg=ENTRY)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_frame, state="disabled", wrap="word",
            bg=ENTRY, fg=FG, insertbackground=FG,
            font=("Courier", 11), relief="solid", bd=1,
            yscrollcommand=scrollbar.set)
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

    def _get_keywords(self) -> list[str]:
        return [e.get().strip() for e in self.keyword_entries if e.get().strip()]

    def _get_schedule_dt(self) -> datetime.datetime:
        now = datetime.datetime.now()
        h = int(self.hour_var.get())
        m = int(self.minute_var.get())
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        return target

    def _on_start(self):
        keywords = self._get_keywords()
        if not keywords:
            messagebox.showwarning("입력 오류", "검색어를 최소 1개 입력해주세요.")
            return
        self.stop_event = threading.Event()
        target_dt = self._get_schedule_dt()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._log("=" * 36)
        self._log(f"검색어: {', '.join(keywords)}")
        self._log(f"실행 예정: {target_dt.strftime('%Y-%m-%d %H:%M:00')}")
        self._log("=" * 36)
        self.worker_thread = threading.Thread(
            target=self._worker, args=(keywords, target_dt), daemon=True)
        self.worker_thread.start()
        self._polling = True
        self._poll_queue()

    def _on_stop(self):
        self.stop_event.set()
        self._log("중지 신호를 보냈습니다...")
        self.stop_btn.config(state="disabled")

    def _on_close(self):
        self.stop_event.set()
        self.root.destroy()

    def _worker(self, keywords: list[str], target_dt: datetime.datetime):
        while not self.stop_event.is_set():
            remaining = (target_dt - datetime.datetime.now()).total_seconds()
            if remaining <= 0:
                break
            mins, secs = int(remaining // 60), int(remaining % 60)
            self.log_queue.put(f"실행까지 {mins}분 {secs}초 남음...")
            self.stop_event.wait(timeout=1.0)
        if not self.stop_event.is_set():
            SearchBot(keywords, self.log_queue.put, self.stop_event).run()
        self.log_queue.put("__DONE__")

    def _log(self, message: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{ts}] {message}")

    def _poll_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__DONE__":
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self._polling = False
                    return
                self.log_text.config(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        if self._polling:
            self.root.after(100, self._poll_queue)

    def run(self):
        self.root.update()
        self.root.mainloop()


if __name__ == "__main__":
    SearchApp().run()
