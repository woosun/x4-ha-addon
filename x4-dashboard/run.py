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


APP_VERSION = "v6.0"


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
POLL_INTERVAL = int(cfg.get("poll_interval", 600))

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


import math


def _icon_sun(d, cx, cy, sz):
    d.ellipse([cx - sz // 2, cy - sz // 2, cx + sz // 2, cy + sz // 2], outline=0, width=2)
    for a in range(0, 360, 45):
        r = math.radians(a); r2 = sz // 2 + 2; r3 = sz // 2 + sz // 4
        d.line([cx + int(r2 * math.cos(r)), cy + int(r2 * math.sin(r)),
                cx + int(r3 * math.cos(r)), cy + int(r3 * math.sin(r))], fill=0, width=2)


def _icon_cloud(d, cx, cy, sz):
    d.ellipse([cx - sz // 2, cy - sz // 3, cx - sz // 6 + sz // 3, cy + sz // 4], outline=0, width=2)
    d.ellipse([cx - sz // 6, cy - sz // 2, cx + sz // 3, cy + sz // 6], outline=0, width=2)
    d.ellipse([cx - sz // 3, cy - sz // 6, cx + sz // 2, cy + sz // 3], outline=0, width=2)
    d.line([cx - sz // 2, cy + sz // 4, cx + sz // 2, cy + sz // 4], fill=0, width=2)


def _icon_pcloud(d, cx, cy, sz):
    _icon_sun(d, cx - sz // 4, cy - sz // 4, sz // 2)
    _icon_cloud(d, cx + sz // 5, cy + sz // 6, sz)


def _icon_rain(d, cx, cy, sz):
    _icon_cloud(d, cx, cy - sz // 6, sz)
    for ox in [-sz // 3, 0, sz // 3]:
        d.line([cx + ox, cy + sz // 4, cx + ox - 2, cy + sz // 2], fill=0, width=2)


def _wicon(d, cond, cx, cy, sz):
    {"sunny": _icon_sun, "partlycloudy": _icon_pcloud, "cloudy": _icon_cloud,
     "rainy": _icon_rain, "pouring": _icon_rain, "snowy": _icon_rain,
     "fog": _icon_cloud, "lightning": _icon_rain, "clear-night": _icon_cloud
     }.get(cond, _icon_sun)(d, cx, cy, sz)


def _hm(iso):
    try:
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        d = _dt.fromisoformat(iso.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=_tz.utc)
        return d.astimezone(_tz(_td(hours=9))).strftime("%H:%M")
    except Exception:
        return iso[11:16] if len(iso) > 10 else "--:--"


def _short_loc(raw):
    if raw in ("--", "외출", ""):
        return "외출"
    parts = raw.replace("대한민국", "").replace("서울특별시", "").strip()
    return " ".join(parts.split())[:14] or "외출"


def render(states):
    img = Image.new("1", (W, H), 255)
    d = ImageDraw.Draw(img)
    f_huge = ImageFont.truetype(FP, 60)
    f_big = ImageFont.truetype(FP, 36)
    f_data = ImageFont.truetype(FP, 30)
    f_info = ImageFont.truetype(FP, 24)
    f_xs = ImageFont.truetype(FP, 18)

    now = datetime.now()
    mx = 10

    st = {}
    for s in states:
        st[s["entity_id"]] = {"state": s.get("state", ""), "attrs": s.get("attributes", {})}

    def val(eid, dflt="--"):
        v = st.get(eid, {}).get("state", "")
        return v if v not in ("unavailable", "unknown", "None", "none", "") else dflt

    def tw(s, font): return d.textlength(s, font=font)
    def tx(x, y, s, font, fill=0): d.text((x, y), s, font=font, fill=fill)
    def txc(cx, y, s, font, fill=0): d.text((cx - tw(s, font) // 2, y), s, font=font, fill=fill)
    def txr(rx, y, s, font, fill=0): d.text((rx - tw(s, font), y), s, font=font, fill=fill)

    x4st = get_x4_status()
    x4_bat = x4st.get("battery", "--")

    today_kwh = 0.0
    for eid in ["sensor.geosileeokeon_energy", "sensor.baegeob_total_energy", "sensor.anmagi_energy"]:
        try:
            today_kwh += float(val(eid, "0"))
        except ValueError:
            pass

    wcond = val("weather.naver_weather_banghag1dong_nalssi_banghag1dong", "sunny")
    ext = val("sensor.naver_weather_banghag1dong_nalssi_hyeonjaeondo")
    feels = val("sensor.naver_weather_banghag1dong_nalssi_cegamondo")
    humid = val("sensor.naver_weather_banghag1dong_nalssi_hyeonjaeseubdo")
    wdir = val("sensor.naver_weather_banghag1dong_nalssi_hyeonjaepunghyang")
    wspeed = val("sensor.naver_weather_banghag1dong_nalssi_hyeonjaepungsog")
    hi = val("sensor.naver_weather_banghag1dong_nalssi_coegoondo")
    lo = val("sensor.naver_weather_banghag1dong_nalssi_coejeoondo")
    rain = val("sensor.naver_weather_banghag1dong_nalssi_gangsuhwagryul")
    pm10 = val("sensor.naver_weather_banghag1dong_nalssi_misemeonji")
    pm10g = val("sensor.naver_weather_banghag1dong_nalssi_misemeonjideunggeub")
    pm25 = val("sensor.naver_weather_banghag1dong_nalssi_comisemeonji")
    pm25g = val("sensor.naver_weather_banghag1dong_nalssi_comisemeonjideunggeub")
    sunrise = _hm(val("sensor.sun_next_rising", ""))
    sunset = _hm(val("sensor.sun_next_setting", ""))
    ac_power = val("sensor.geosileeokeon_power", "0")

    period = "오전" if now.hour < 12 else "오후"
    h12 = now.strftime("%I:%M").lstrip("0")

    HEADER_H = 52
    tx(mx, 0, f"업데이트 {h12}", f_big, 0)
    tx(mx + tw(f"업데이트 {h12}", f_big) + 8, 10, APP_VERSION, f_info, 0)
    txr(W - mx, 0, f"{X4_IP}", f_info, 0)
    txr(W - mx, 24, f"배터리 {x4_bat}% · 오늘 {today_kwh:.1f}kWh", f_info, 0)
    txc(W // 2, 14, date_ko(now), f_info, 0)
    d.line((mx, HEADER_H, W - mx, HEADER_H), fill=0, width=2)

    left_w = 500; col_r = 510; top = HEADER_H + 6
    d.line((left_w, top, left_w, H - 8), fill=0, width=1)

    lx = mx; y = top
    tx(lx, y, f"{ext}'", f_huge, 0)
    _wx = lx + int(tw(f"{ext}'", f_huge)) + 26
    _wicon(d, wcond, _wx, y + 28, 38)
    tx(_wx + 50, y + 4, "방학1동", f_info, 0)
    y += 60

    tx(lx, y, f"체감 {feels}' 습도 {humid}%  {wdir} {wspeed}m/s", f_info, 0); y += 26
    tx(lx, y, f"최고 {hi}' 최저 {lo}'  비안옴 {rain}%", f_info, 0); y += 26
    tx(lx, y, f"일출 {sunrise} 일몰 {sunset}  미세 {pm10}({pm10g}) 초미세 {pm25}({pm25g})", f_xs, 0); y += 22

    d.line((lx, y, left_w - 6, y), fill=0, width=1); y += 6
    fcw = left_w - lx - 10; cw = fcw // 5
    forecast = get_weekly_forecast()
    for i, (weekday, cond, dlo, dhi, drain) in enumerate(forecast[:5]):
        cx = lx + i * cw; ccx = cx + cw // 2
        tx(ccx, y, weekday, f_info, 0)
        _wicon(d, cond, ccx, y + 46, 26)
        txc(cx + cw // 2, y + 74, f"{dhi}'", f_data, 0)
        txc(cx + cw // 2, y + 110, f"{dlo}'", f_info, 0)
    y += 138

    d.line((lx, y, left_w - 6, y), fill=0, width=1); y += 6
    tx(lx, y, "실내", f_info, 0); y += 28
    rooms = [
        ("거실", val("sensor.geosilrimokeon_ondo"), val("sensor.geosilrimokeon_seubdo")),
        ("안방", val("sensor.anbang_onseubdo_temperature"), val("sensor.anbang_onseubdo_humidity")),
        ("내방", val("sensor.zhimi_ma2_caaf_indoor_temperature"), val("sensor.zhimi_ma2_caaf_relative_humidity")),
        ("베란다", val("sensor.berandaonseubdo_temperature"), val("sensor.berandaonseubdo_humidity")),
        ("화장실", val("sensor.hwajangsilonseubdo_temperature"), val("sensor.hwajangsilonseubdo_humidity")),
        ("보일러", val("sensor.boilreosilonseubdo_temperature"), val("sensor.boilreosilonseubdo_humidity")),
    ]
    col_w = (left_w - lx - 16) // 2
    for i, (nm, t, h) in enumerate(rooms):
        bx = lx + (i % 2) * (col_w + 16); ry = y + (i // 2) * 32
        tx(bx, ry, f"{nm} {t}'", f_info, 0)
        txr(bx + col_w, ry, f"{h}%", f_info, 0)

    iy = top
    tx(col_r, iy, "가족", f_big, 0); iy += 38
    people = [
        ("아버지", "person.abuji", "sensor.abuji_geocoded_location"),
        ("어무니", "person.jhs600110", "sensor.unknown_geocoded_location"),
        ("우선", "person.woosun", "sensor.useonipoldeu_geocoded_location"),
    ]
    for name, person_eid, geo_eid in people:
        state = val(person_eid)
        present = state == "home"
        mark = "O" if present else "X"
        loc = "재실" if present else _short_loc(val(geo_eid, "외출"))
        tx(col_r, iy, f"[{mark}] {name}", f_info, 0)
        if len(loc) <= 4:
            txr(W - mx, iy + 2, loc, f_info, 0)
        else:
            txr(W - mx, iy + 2, loc, f_xs, 0)
        iy += 28

    iy += 4; d.line((col_r, iy, W - mx, iy), fill=0, width=1); iy += 6
    tx(col_r, iy, "도어", f_info, 0); iy += 28
    doors = [
        ("현관문", "binary_sensor.hyeongwanmun_contact"),
        ("중문", "binary_sensor.jungmun_contact"),
        ("에어컨문", "binary_sensor.eeokeon_contact"),
    ]
    for nm, eid in doors:
        stt_raw = val(eid, "off")
        closed = stt_raw == "off"
        mark = "O" if closed else "X"
        stt = "닫힘" if closed else "열림"
        extra = f"  {ac_power}W" if nm == "에어컨문" else ""
        tx(col_r, iy, f"[{mark}] {nm}", f_xs, 0)
        txr(W - mx, iy, f"{stt}{extra}", f_xs, 0)
        iy += 26

    iy += 4; d.line((col_r, iy, W - mx, iy), fill=0, width=1); iy += 6
    pve_cpu = val("sensor.node_pve_cpu_used", "0")
    pve_ram = val("sensor.node_pve_memory_used_percentage", "0")
    nvme_t = val("sensor.disk_pve_k2_temperature", "--")
    ssd_t = val("sensor.disk_pve_ssstc_cl4_8d256_temperature", "--")
    try:
        cpu_pct = f"{float(pve_cpu):.0f}"
    except ValueError:
        cpu_pct = "0"
    try:
        ram_pct = f"{float(pve_ram):.0f}"
    except ValueError:
        ram_pct = "0"
    tx(col_r, iy, "PVE 서버", f_info, 0); iy += 26
    tx(col_r, iy, f"CPU {cpu_pct}%  RAM {ram_pct}%", f_info, 0); iy += 26
    tx(col_r, iy, f"NVMe {nvme_t}° SSD {ssd_t}°", f_info, 0); iy += 30

    iy += 2; d.line((col_r, iy, W - mx, iy), fill=0, width=1); iy += 6
    zai = val("sensor.z_ai_token_limit", "--")
    zai_num = int(zai) if zai.isdigit() else 0
    zai_reset = val("sensor.z_ai_rises_sigan", "--")
    if zai_reset != "--" and len(zai_reset) > 10:
        zai_reset = zai_reset[11:16]
    tx(col_r, iy, f"Z.AI 잔여 {max(0, 100 - zai_num)}%", f_data, 0); iy += 34
    tx(col_r, iy, f"리셋 {zai_reset}", f_info, 0); iy += 28

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
    # Send as multipart form-data (same proven path as /upload).
    b = "----X4WIN"
    crlf = b"\r\n"
    body = b"".join([
        b"--" + b.encode() + crlf,
        b'Content-Disposition: form-data; name="region"; filename="r.bin"' + crlf,
        b"Content-Type: application/octet-stream" + crlf + crlf,
        bytes(region) + crlf,
        b"--" + b.encode() + b"--" + crlf,
    ])
    url = (f"http://{X4_IP}/window?x={x}&y={y}&w={w}&h={h}")
    headers = {"Content-Type": f"multipart/form-data; boundary={b}"}
    if X4_TOKEN:
        headers["X-X4-Token"] = X4_TOKEN
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
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
