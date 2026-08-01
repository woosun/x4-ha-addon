#!/usr/bin/env python3
"""X4 E-Paper Dashboard — HA Add-on v5.1.

Extra large fonts. Simplified to fit 800x480.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta

import os
os.environ.setdefault("TZ", "Asia/Seoul")
import time as _time
_time.tzset()

from PIL import Image, ImageDraw, ImageFont


APP_VERSION = "v5.7"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def date_ko(dt):
    wd = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
    return f"{dt.month}월 {dt.day}일 ({wd})"


cfg = json.load(open("/data/options.json"))
X4_IP = cfg.get("x4_ip", "")
X4_TOKEN = cfg.get("x4_token", "")
HA_URL = cfg.get("ha_url", "http://homeassistant:8123").rstrip("/")
HA_TOKEN = cfg.get("ha_token", "")
POLL_INTERVAL = int(cfg.get("poll_interval", 60))

W, H = 800, 480
FS = W * H // 8
FP = "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc"

COND_TEXT = {"sunny": "맑음", "partlycloudy": "구름", "cloudy": "흐림",
             "rainy": "비", "pouring": "폭우", "snowy": "눈", "fog": "안개",
             "lightning": "뇌우", "clear-night": "맑음"}


def ha_get_all():
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}
    req = urllib.request.Request(f"{HA_URL}/api/states", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"[ha] {e}")
        return []


def get_x4_status():
    try:
        with urllib.request.urlopen(f"http://{X4_IP}/status", timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def get_weekly_forecast():
    try:
        url = f"{HA_URL}/api/services/weather/get_forecasts?return_response=true"
        body = json.dumps({"entity_id": "weather.naver_weather_banghag1dong_nalssi_banghag1dong", "type": "daily"}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
        forecasts = d.get("service_response", {}).get(
            "weather.naver_weather_banghag1dong_nalssi_banghag1dong", {}).get("forecast", [])
        from datetime import datetime as dt
        result = []
        for i, f in enumerate(forecasts[:5]):
            dt_str = f.get("datetime", "")
            try:
                d_date = dt.strptime(dt_str[:10], "%Y-%m-%d")
                weekday = ["월","화","수","목","금","토","일"][d_date.weekday()]
            except Exception:
                weekday = ""
            cond = COND_TEXT.get(f.get("condition", ""), "-")
            tlo = f"{f.get('templow', 0):.0f}"
            thi = f"{f.get('temperature', 0):.0f}"
            rain = f.get("precipitation_probability", 0)
            result.append((weekday, cond, tlo, thi, rain))
        return result
    except Exception as e:
        log(f"[forecast] {e}")
        return []


def get_power_history(now):
    daily_usage = []
    try:
        energy_eids = "sensor.geosileeokeon_energy,sensor.baegeob_total_energy,sensor.anmagi_energy"
        start_dt = now - timedelta(days=7)
        hist_url = (f"{HA_URL}/api/history/period/{start_dt.strftime('%Y-%m-%dT%H:%M:%S')}"
                    f"?filter_entity_id={energy_eids}&end_time={now.strftime('%Y-%m-%dT%H:%M:%S')}&minimal_response")
        hist_req = urllib.request.Request(hist_url, headers={"Authorization": f"Bearer {HA_TOKEN}"})
        with urllib.request.urlopen(hist_req, timeout=12) as hr:
            hist_data = json.loads(hr.read())
        day_vals = defaultdict(float)
        for device_hist in (hist_data or []):
            day_min, day_max = {}, {}
            for point in device_hist:
                try:
                    v = float(point.get("state", 0))
                except (ValueError, TypeError):
                    continue
                day = point.get("last_changed", "")[:10]
                if day not in day_min:
                    day_min[day] = v
                    day_max[day] = v
                day_min[day] = min(day_min[day], v)
                day_max[day] = max(day_max[day], v)
            for day in day_max:
                day_vals[day] += day_max[day] - day_min[day]
        for i in range(7):
            d_dt = (now - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            daily_usage.append(day_vals.get(d_dt, 0.0))
    except Exception:
        daily_usage = [0.0] * 7
    return daily_usage


def render(states):
    img = Image.new("1", (W, H), 255)
    d = ImageDraw.Draw(img)

    # EXTRA LARGE FONTS
    f_temp = ImageFont.truetype(FP, 64)    # main weather temp
    f_big = ImageFont.truetype(FP, 36)     # time, headers
    f_data = ImageFont.truetype(FP, 30)    # room temps, values
    f_info = ImageFont.truetype(FP, 22)    # labels, sub-info
    f_xs = ImageFont.truetype(FP, 16)      # footer only

    now = datetime.now()
    mx = 10

    st = {}
    for s in states:
        st[s["entity_id"]] = {"state": s.get("state", ""), "attrs": s.get("attributes", {})}

    def val(eid, dflt="--"):
        v = st.get(eid, {}).get("state", "")
        return v if v not in ("unavailable", "unknown", "") else dflt

    def tw(s, font): return d.textlength(s, font=font)
    def tx(x, y, s, font, fill=0): d.text((x, y), s, font=font, fill=fill)
    def txr(rx, y, s, font, fill=0): d.text((rx - tw(s, font), y), s, font=font, fill=fill)

    x4st = get_x4_status()
    x4_bat = x4st.get("battery", "--")

    total_w = 0
    for pid in ["sensor.geosileeokeon_power", "sensor.baegeob_power", "sensor.anmagi_power"]:
        try: total_w += float(val(pid, "0"))
        except ValueError: pass

    wcond = val("sensor.naver_weather_banghag1dong_nalssi_hyeonjaenalssi")

    period = "오전" if now.hour < 12 else "오후"
    h12 = now.strftime("%I:%M").lstrip("0")
    tx(mx, 0, f"{period} {h12}", f_big, 0)
    tx(mx + tw(f"{period} {h12}", f_big) + 8, 10, APP_VERSION, f_info, 0)
    _ds = date_ko(now)
    tx((W - tw(_ds, f_info)) // 2, 6, _ds, f_info, 0)
    x4b = "--" if x4_bat == "--" else f"{x4_bat}%"
    txr(W - mx, 7, f"{X4_IP} · 배터리 {x4b} · {total_w:.0f}W", f_info, 0)

    # ── LAYOUT ──────────────────────────────────────────────
    left_w = 460
    col_r = left_w + 6
    HEADER_H = 48
    top = HEADER_H + 4
    d.line((left_w, top, left_w, H - 14), fill=0, width=1)

    # ═══ LEFT: WEATHER + FORECAST + POWER ═══
    lx = mx
    y = top

    # Weather — giant temp
    ext = val("sensor.naver_weather_banghag1dong_nalssi_hyeonjaeondo")
    tx(lx, y, f"{ext}'", f_temp, 0)
    txr(left_w - 4, y + 8, wcond, f_big, 0)
    y += 72

    feels = val("sensor.naver_weather_banghag1dong_nalssi_cegamondo")
    humid = val("sensor.naver_weather_banghag1dong_nalssi_hyeonjaeseubdo")
    tx(lx, y, f"체감 {feels}' 습도 {humid}%", f_info, 0)
    y += 26

    hi = val("sensor.naver_weather_banghag1dong_nalssi_coegoondo")
    lo = val("sensor.naver_weather_banghag1dong_nalssi_coejeoondo")
    tx(lx, y, f"최고 {hi}' 최저 {lo}'", f_info, 0)
    y += 28

    # Forecast — bigger
    d.line((lx, y, left_w - 4, y), fill=0, width=1)
    y += 4
    forecast = get_weekly_forecast()
    fcw = left_w - lx - 8
    col_w = fcw // 5
    for i, (weekday, cond, dlo, dhi, drain) in enumerate(forecast[:5]):
        cx = lx + i * col_w
        tx(cx + 2, y, weekday, f_info, 0)
        tx(cx + 2, y + 24, cond, f_xs, 0)
        tx(cx + 2, y + 44, f"{dhi}'", f_data, 0)
        tx(cx + 2, y + 78, f"{dlo}'", f_info, 0)
    y += 110 if forecast else 0

    # Power chart
    d.line((lx, y, left_w - 4, y), fill=0, width=1)
    y += 4
    tx(lx, y, "주간 전력", f_info, 0)
    y += 4

    daily_usage = get_power_history(now)
    # Leave room inside the chart box for the kWh point labels.
    ct = y + 22
    cb = H - 20
    cl = lx + 4
    cr = left_w - 8
    ch = cb - ct
    cwd = cr - cl

    d.rectangle([cl, ct, cr, cb], outline=0, width=1)
    max_v = max(daily_usage) if daily_usage else 1
    max_v = max(max_v, 0.1)
    n = len(daily_usage)
    if n > 1:
        pts = []
        for i, v in enumerate(daily_usage):
            px = cl + int(cwd * i / (n - 1))
            # Top value must not sit at the very top edge; keep >= ct+LABEL_H so label fits above.
            LABEL_H = 16
            max_pt = cb - 1
            min_pt = ct + LABEL_H
            ppt = max_pt - int((max_pt - min_pt) * min(v / max_v, 1.0))
            pts.append((px, ppt))
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=0, width=2)
        for i, (px, ppt) in enumerate(pts):
            d.ellipse([px - 2, ppt - 2, px + 2, ppt + 2], fill=0)
            kwh_str = f"{daily_usage[i]:.1f}"
            # Clamp label inside the box horizontally.
            lw = tw(kwh_str, f_xs)
            lx_p = px - lw // 2
            lx_p = max(cl + 1, min(lx_p, cr - lw - 1))
            tx(lx_p, ppt - LABEL_H, kwh_str, f_xs, 0)

    # ═══ RIGHT: INDOOR + FAMILY + Z.AI ═══
    iy = top
    tx(col_r, iy, "실내", f_big, 0)
    iy += 42

    rooms = [
        ("거실", val("sensor.geosilrimokeon_ondo"), val("sensor.geosilrimokeon_seubdo")),
        ("안방", val("sensor.anbang_onseubdo_temperature"), val("sensor.anbang_onseubdo_humidity")),
        ("내방", val("sensor.zhimi_ma2_caaf_indoor_temperature"), val("sensor.zhimi_ma2_caaf_relative_humidity")),
        ("베란다", val("sensor.berandaonseubdo_temperature"), val("sensor.berandaonseubdo_humidity")),
    ]

    for name, t, h in rooms:
        tx(col_r, iy, name, f_data, 0)
        tx(col_r + 80, iy, f"{t}'", f_data, 0)
        txr(W - mx, iy + 4, f"{h}%", f_info, 0)
        iy += 34

    # Family
    iy += 6
    d.line((col_r, iy, W - mx, iy), fill=0, width=1)
    iy += 4
    tx(col_r, iy, "가족", f_big, 0)
    iy += 38

    people = [
        ("아버지", "person.abuji", "sensor.abuji_geocoded_location"),
        ("어무니", "person.jhs600110", "sensor.unknown_geocoded_location"),
        ("우선", "person.woosun", "sensor.useonipoldeu_geocoded_location"),
    ]

    for name, person_eid, geo_eid in people:
        state = val(person_eid)
        present = state == "home"
        mark = "O" if present else "X"
        loc = "재실" if present else "외출"
        if not present:
            raw = val(geo_eid, "외출")
            parts = raw.replace("대한민국", "").replace("서울특별시", "").strip()
            loc = " ".join(parts.split())[:10] or "외출"
        tx(col_r, iy, f"[{mark}] {name}", f_info, 0)
        txr(W - mx, iy + 2, loc, f_info, 0)
        iy += 26

    # Z.AI
    iy += 4
    d.line((col_r, iy, W - mx, iy), fill=0, width=1)
    iy += 4
    zai = val("sensor.z_ai_token_limit", "--")
    zai_num = int(zai) if zai.isdigit() else 0
    zai_reset = val("sensor.z_ai_rises_sigan", "--")
    if zai_reset != "--" and len(zai_reset) > 10:
        zai_reset = zai_reset[11:16]
    zai_remain = max(0, 100 - zai_num)
    tx(col_r, iy, f"Z.AI 잔여 : {zai_remain}%", f_data, 0)
    iy += 30
    tx(col_r, iy, f"리셋시간 : {zai_reset}", f_info, 0)
    iy += 24

    # ── FOOTER ──────────────────────────────────────────────
    d.line((mx, H - 10, W - mx, H - 10), fill=0, width=1)
    tx(mx, H - 7, f"HA {now.strftime('%H:%M')}", f_xs, 0)

    raw = img.tobytes()
    assert len(raw) == FS
    return raw


def push(frame):
    b = "----X4FB"
    crlf = b"\r\n"
    body = b"".join([
        b"--" + b.encode() + crlf,
        b'Content-Disposition: form-data; name="frame"; filename="f.bin"' + crlf,
        b"Content-Type: application/octet-stream" + crlf + crlf,
        frame + crlf,
        b"--" + b.encode() + b"--" + crlf,
    ])
    headers = {"Content-Type": f"multipart/form-data; boundary={b}"}
    if X4_TOKEN:
        headers["X-X4-Token"] = X4_TOKEN
    req = urllib.request.Request(f"http://{X4_IP}/upload", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        log(f"[push] {e}")
        return False


# ── Windowed (partial) refresh ──────────────────────────────────
# Find the byte-aligned bounding box of pixels that changed between the
# previous and current frames. Returns (x, y, w, h) in pixels or None.
WB = W // 8  # bytes per row


def bbox_changed(prev, cur):
    if prev is None:
        return None
    min_bx = max_bx = min_y = max_y = None
    for y in range(H):
        off = y * WB
        if cur[off:off + WB] == prev[off:off + WB]:
            continue
        for bx in range(WB):
            if cur[off + bx] != prev[off + bx]:
                if min_bx is None or bx < min_bx:
                    min_bx = bx
                if max_bx is None or bx > max_bx:
                    max_bx = bx
        if min_y is None or y < min_y:
            min_y = y
        if max_y is None or y > max_y:
            max_y = y
    if min_bx is None:
        return None  # no change
    return min_bx, max_bx, min_y, max_y


def push_window(frame, min_bx, max_bx, min_y, max_y):
    x = min_bx * 8
    w = (max_bx - min_bx + 1) * 8
    y = min_y
    h = max_y - min_y + 1
    # Build the region bytes row by row.
    region = bytearray()
    for r in range(y, y + h):
        off = r * WB + min_bx
        region += frame[off:off + (w // 8)]
    url = (f"http://{X4_IP}/window?x={x}&y={y}&w={w}&h={h}")
    headers = {"Content-Type": "application/octet-stream"}
    if X4_TOKEN:
        headers["X-X4-Token"] = X4_TOKEN
    req = urllib.request.Request(url, data=bytes(region), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        log(f"[push_window] {e}")
        return False


FULL_AREA = W * H
WINDOW_THRESHOLD = 0.6  # if changed bbox exceeds 60% of screen, send full frame instead


def main():
    log(f"{APP_VERSION} starting — X4={X4_IP} interval={POLL_INTERVAL}s")
    prev_frame = None
    last_x4_count = -1
    while True:
        try:
            states = ha_get_all()
            if not states:
                log("no HA data")
                time.sleep(10)
                continue
            frame = render(states)
            same = (prev_frame == frame)
            if same:
                log("unchanged")
                time.sleep(POLL_INTERVAL)
                continue
            # Detect device reboot: if refresh_count dropped, its framebuffer was
            # reset, so a full push is required to re-establish the whole screen.
            x4st = get_x4_status()
            x4_count = x4st.get("refresh_count", -1)
            rebooted = isinstance(x4_count, int) and x4_count < last_x4_count
            last_x4_count = x4_count if isinstance(x4_count, int) else last_x4_count

            bb = bbox_changed(prev_frame, frame)
            use_window = False
            if prev_frame is not None and not rebooted and bb is not None:
                _, max_bx, _, max_y = bb
                min_bx, _, min_y, _ = bb
                w = (max_bx - min_bx + 1) * 8
                h = max_y - min_y + 1
                use_window = (w * h) < (FULL_AREA * WINDOW_THRESHOLD)

            if use_window:
                ok = push_window(frame, min_bx, max_bx, min_y, max_y)
                log("pushed (window)" if ok else "push failed (window)")
            else:
                ok = push(frame)
                log("pushed (full)" if ok else "push failed")
            if ok:
                prev_frame = frame
        except Exception as e:
            log(f"error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
