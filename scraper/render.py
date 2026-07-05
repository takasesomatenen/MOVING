"""HTML を Chromium(Playwright) で PNG / PDF に描画するヘルパー。

このサンドボックスは外部ネットワーク遮断だが、ローカル HTML の描画は
プリインストールの Chromium で可能(ネット不要)。日本語は IPAGothic で描画。
"""

import glob
import os
import sys
from playwright.sync_api import sync_playwright


def _chromium_path():
    # プリインストールの Chromium を直接指す(playwright install は不可)。
    env = os.environ.get("CHROMIUM_PATH")
    if env and os.path.exists(env):
        return env
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def render(html_path, png_path=None, pdf_path=None, width=900, full_page=True):
    exe = _chromium_path()
    html_path = os.path.abspath(html_path)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": width, "height": 1400},
                                device_scale_factor=2)
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(400)
        if png_path:
            page.screenshot(path=png_path, full_page=full_page)
        if pdf_path:
            page.emulate_media(media="screen")
            page.pdf(path=pdf_path, print_background=True,
                     width=f"{width}px", prefer_css_page_size=True)
        browser.close()


if __name__ == "__main__":
    html = sys.argv[1]
    png = sys.argv[2] if len(sys.argv) > 2 else None
    pdf = sys.argv[3] if len(sys.argv) > 3 else None
    render(html, png, pdf)
    print("rendered:", png, pdf)
