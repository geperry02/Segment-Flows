"""Download KM TGP Segment Capacity Excel exports, one per gas day + cycle.

The page is an ASP.NET / Infragistics form, so we drive it with a headless browser:
set the date picker and cycle dropdown, click Retrieve, then click Download (EXCEL).
All browser traffic is relayed through `requests`, which keeps one cookie session
(the site pins sessions to a backend server) and uses the system/proxy CA bundle.
"""

import shutil
import tempfile
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

from .config import KM_URL
from .report import parse_report

PREFIX = "WebSplitter1_tmpl1_ContentPlaceHolder1_"
DATE_PICKER = PREFIX + "dtePickerBegin"
CYCLE_DD = PREFIX + "ddlCycleDD"
RETRIEVE = "#" + PREFIX + "HeaderBTN1_btnRetrieve"
DOWNLOAD = "#" + PREFIX + "HeaderBTN1_btnDownload"

SET_INPUTS_JS = """([y, m, d, cycle]) => {
  $find('%s').set_value(new Date(y, m - 1, d));
  const dd = $find('%s'), items = dd.get_items();
  for (let i = 0; i < items.getLength(); i++) {
    if (items.getItem(i).get_text() === cycle) {
      dd.selectItemByIndex(i, true, true);
      dd.set_currentValue(cycle, true);
      return true;
    }
  }
  return false;
}""" % (DATE_PICKER, CYCLE_DD)


class KMFetcher:
    def __init__(self, browser_path=None, delay=1.0):
        self.browser_path = browser_path
        self.delay = delay
        self.session = requests.Session()

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(executable_path=self.browser_path)
        self._open_page()
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def _relay(self, route):
        req = route.request
        headers = {k: v for k, v in req.headers.items() if k.lower() != "cookie"}
        resp = self.session.request(req.method, req.url, headers=headers,
                                    data=req.post_data_buffer, allow_redirects=False, timeout=120)
        drop = {"content-encoding", "transfer-encoding", "content-length"}
        route.fulfill(status=resp.status_code, body=resp.content,
                      headers={k: v for k, v in resp.headers.items() if k.lower() not in drop})

    def _open_page(self):
        self._context = self._browser.new_context(accept_downloads=True)
        self._context.route("**/*", self._relay)
        self.page = self._context.new_page()
        self.page.goto(KM_URL, wait_until="networkidle", timeout=180000)

    def _reset(self):
        self._context.close()
        self.session = requests.Session()
        self._open_page()

    def download(self, day, km_cycle, dest):
        """Save the report for `day` / `km_cycle` to `dest`, verifying its header."""
        page = self.page
        if not page.evaluate(SET_INPUTS_JS, [day.year, day.month, day.day, km_cycle]):
            raise RuntimeError(f"Cycle {km_cycle!r} not in KM dropdown")
        with page.expect_response(lambda r: r.request.method == "POST", timeout=180000):
            page.click(RETRIEVE)
        page.wait_for_load_state("networkidle", timeout=180000)
        with page.expect_download(timeout=180000) as info:
            page.click(DOWNLOAD)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_file = Path(tmp) / "report.xlsx"
            info.value.save_as(tmp_file)
            report = parse_report(tmp_file)
            if report.gas_day.date() != day or report.cycle != km_cycle:
                raise RuntimeError(f"KM returned {report.gas_day:%m/%d/%Y} {report.cycle} "
                                   f"instead of {day:%m/%d/%Y} {km_cycle}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp_file, dest)
        time.sleep(self.delay)

    def download_with_retry(self, day, km_cycle, dest, attempts=3):
        for attempt in range(1, attempts + 1):
            try:
                return self.download(day, km_cycle, dest)
            except Exception as exc:  # noqa: BLE001 - network/page hiccups; retry fresh
                if attempt == attempts:
                    raise
                print(f"    retry {attempt} after error: {exc}")
                self._reset()
