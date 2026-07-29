"""Fetch TAIFEX's official 臺指選擇權波動率指數 (Taiwan VIX).

TAIFEX only publishes a rolling window of recent months for free
(older months 404). This returns whatever is currently available.
"""
import requests

TAIFEX_URL = "https://www.taifex.com.tw/file/taifex/Dailydownload/vix/log2data/{ym}new.txt"


def fetch_taiwan_vix(months_back=6):
    """Return {'YYYY-MM-DD': float} of real TAIFEX Taiwan VIX closes."""
    result = {}
    from datetime import datetime
    today = datetime.now()
    y, m = today.year, today.month
    for _ in range(months_back):
        ym = f"{y}{m:02d}"
        try:
            resp = requests.get(TAIFEX_URL.format(ym=ym), timeout=10)
            if resp.status_code == 200 and resp.content:
                text = resp.content.decode("big5", errors="ignore")
                for line in text.splitlines():
                    parts = line.split("\t")
                    date_part = parts[0].strip()
                    if len(parts) >= 5 and date_part.isdigit() and len(date_part) == 8:
                        date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                        value = next((p for p in parts[2:] if p.strip()), None)
                        if value is not None:
                            try:
                                result[date_str] = float(value)
                            except ValueError:
                                pass
        except requests.RequestException:
            pass
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return result
