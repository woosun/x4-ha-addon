# 사용 엔티티 참조

이 문서는 화면의 각 영역이 어떤 Home Assistant 엔티티를 사용하는지 정리합니다.
화면에 이상이 있으면 대부분 아래 엔티티가 실제로 존재하는지, 값이 `unavailable`/`unknown`이 아닌지부터 확인하세요.

> 주의: `config.yaml`의 `entities` 목록과 `run.py` 안의 하드코딩 엔티티가 병행 사용됩니다.
> 엔티티를 추가/제거할 때는 **두 곳을 함께** 맞춰야 합니다.

---

## 날씨 — 실시간 (Naver Weather)

| 엔티티 | 화면 표시 | 비고 |
|---|---|---|
| `sensor.naver_weather_..._hyeonjaeondo` | 현재 온도 (큰 글씨) | |
| `sensor.naver_weather_..._cegamondo` | 체감 온도 | |
| `sensor.naver_weather_..._hyeonjaeseubdo` | 습도 | |
| `sensor.naver_weather_..._coegoondo` | 최고 온도 | |
| `sensor.naver_weather_..._coejeoondo` | 최저 온도 | |
| `sensor.naver_weather_..._hyeonjaenalssi` | 현재 날씨 조건 | `sunny`/`rainy` 등 |
| `sensor.naver_weather_..._misemeonji` | (예비) 미세먼지 | |
| `sensor.naver_weather_..._misemeonjideunggeub` | (예비) 미세먼지 등급 | |
| `sensor.naver_weather_..._comisemeonji` | (예비) 초미세먼지 | |
| `sensor.naver_weather_..._comisemeonjideunggeub` | (예비) 초미세먼지 등급 | |
| `sensor.naver_weather_..._gangsuhwagryul` | (예비) 강수확률 | |
| `sensor.naver_weather_..._hyeonjaepungsog` | (예비) 풍속 | |

## 날씨 — 주간 예보

`run.py`의 `get_weekly_forecast()`가 `weather.naver_weather_banghag1dong_nalssi_banghag1dong` 엔티티의
`weather.get_forecasts` 서비스(일별)를 호출해 5일 예보를 가져옵니다.
개별 `_naeil...` 센서는 화면의 주간 예보에는 쓰이지 않고(HA 설정 증거용), 예보는 위 서비스를 통해 얻습니다.

관련 센서 목록 (`config.yaml`에 포함):

- `sensor.naver_weather_banghag1dong_nalssi_naeilohunalssi`
- `sensor.naver_weather_banghag1dong_nalssi_naeilcoegoondo`
- `sensor.naver_weather_banghag1dong_nalssi_naeilcoejeoondo`
- `sensor.naver_weather_banghag1dong_nalssi_gangsuhwagryul`

---

## 실내 온·습도

| 방 | 온도 엔티티 | 습도 엔티티 |
|---|---|---|
| 거실 | `sensor.geosilrimokeon_ondo` | `sensor.geosilrimokeon_seubdo` |
| 안방 | `sensor.anbang_onseubdo_temperature` | `sensor.anbang_onseubdo_humidity` |
| 내방 | `sensor.zhimi_ma2_caaf_indoor_temperature` | `sensor.zhimi_ma2_caaf_relative_humidity` |
| 베란다 | `sensor.berandaonseubdo_temperature` | `sensor.berandaonseubdo_humidity` |

`config.yaml`에는 베란다 외에 다음과 같은 예비 센서도 있습니다:
- `sensor.boilreosilonseubdo_temperature`
- `sensor.boilreosilonseubdo_humidity`

---

## 전력

화면 **우측 상단의 "총 전력"(W)** 은 `sensor.geosileeokeon_power`, `sensor.baegeob_power`,
`sensor.anmagi_power` 의 **현재 상태 합계**입니다.

**주간 전력 그래프(kWh)** 는 `get_power_history()`가 다음 에너지 엔티티의 7일 history를 읽어 일별
`최대-최소`를 합산한 값을 사용합니다:

- `sensor.geosileeokeon_energy`
- `sensor.baegeob_total_energy`
- `sensor.anmagi_energy`

> 이 에너지 엔티티는 `config.yaml`의 `entities` 목록에는 **없고**, `run.py`에 하드코딩되어 있습니다.
> 그래프 데이터가 비어 있으면 (`0.0`) 이 에너지 센서가 실제로 기록을 쌓고 있는지 확인하세요.

---

## 가족 위치

| 표시 이름 | person 엔티티 | 위치(주소) 센서 |
|---|---|---|
| 아버지 | `person.abuji` | `sensor.abuji_geocoded_location` |
| 어무니 | `person.jhs600110` | `sensor.unknown_geocoded_location` |
| 우선 | `person.woosun` | `sensor.useonipoldeu_geocoded_location` |

- person 상태가 `home`이면 `[O] 재실`, 아니면 `[X]` + 위치 센서 주소.
- 위치 주소에서 `대한민국`/`서울특별시` 접두어를 제거하고 최대 10자로 표시.

> `sensor.unknown_geocoded_location`은 어무니의 geo 센서로, 실제 엔티티명이 다르면
> `run.py`의 `people` 리스트를 수정해야 합니다.

---

## Z.AI 토큰

| 엔티티 | 화면 표시 |
|---|---|
| `sensor.z_ai_token_limit` | 사용률 % → `Z.AI 잔여 : (100-사용)%` |
| `sensor.z_ai_rises_sigan` | 리셋 시각 → `리셋시간 : HH:MM` |

---

## 그 외

- `vacuum.robongi`: `config.yaml`에 있지만 현재 화면 표시용으로는 쓰이지 않는 예비 엔티티입니다.
