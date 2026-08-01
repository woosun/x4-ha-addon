# X4 E-Paper Dashboard (HA Add-on)

Xteink X4 전자종이를 Home Assistant가 그린 800×480 1-bit 화면을 표시하는 홈 모니터 대시보드 HA Add-on 입니다.

애드온은 HAOS에서 60초(기본)마다 Home Assistant 센서를 읽어 프레임을 만들고, X4의 `/upload` 엔드포인트로 직접 푸시합니다. 별도의 중간 서버가 필요 없습니다.

---

## 요구 사항

- Home Assistant OS (HAOS) 또는 Home Assistant Container의 Supervisor 기반 애드온을 실행할 수 있는 환경
- Xteink X4 전자종이 기기 (Wi-Fi 연결, tcp 서버 동작)
- 온습도, 전력, 가족 위치, Z.AI 토큰 센서 등 화면에 필요한 HA 센서

> 실제로 쓰는 센서는 `config.yaml`의 `entities` 목록과 `run.py`의 하드코딩된 엔티티로 병행됩니다. 센서를 바꾸려면 두 곳을 함께 맞춰야 합니다.

---

## 설치 (애드온 저장소 추가)

1. HAOS → 설정 → **애드온 → 애드온 저장소**
2. 저장소 URL에 아래를 추가:
   ```
   https://github.com/woosun/x4-ha-addon
   ```
3. **X4 E-Paper Dashboard** 애드온 설치
4. 구성에서 아래 항목 입력 후 저장
5. **시작**

> slug 는 `x4_paper` 입니다. 이전에 `x4_dash`(구 slug)를 설치했던 적이 있으면, HAOS의 **이미지/애드온 캐시** 때문에 새 버전이 반영되지 않는 경우가 있습니다. 그럴 땐 기존 애드온을 삭제한 뒤 다시 설치하세요.

---

## 구성 옵션 (`config.yaml`)

| 키 | 설명 |
|---|---|
| `x4_ip` | X4 전자종이의 IP (예: `192.168.0.144`) |
| `x4_token` | X4 접근 토큰 (선택) |
| `ha_url` | Home Assistant 주소 (기본 `http://homeassistant:8123`) |
| `ha_token` | Home Assistant 장기 액세스 토큰 |
| `poll_interval` | 화면 갱신 주기(초), `10~3600` 기본 `60` |
| `entities` | 참조할 센서 목록 (HA `/api/states` 조회용) |

`ha_token`은 Supervisor 인입 주소(`http://supervisor/core/api`)가 아니라 **직접 접근 가능한 HA URL**에 맞는 토큰이어야 합니다.

---

## 화면 구성 (800×480)

### 상단 헤더
- 왼쪽: `오전/오후` + 12시간제 시각 + 애드온 버전
- 중앙: 날짜 (예: `8월 1일 (토)`)
- 오른쪽: `X4 IP · 배터리% · 총전력W`

### 왼쪽 열 (460px)
- **날씨**: 현재 온도(큰 글씨), 조건, 체감/습도, 최고/최저
- **주간 예보**: 5일 (요일·날씨·최고/최저)
- **주간 전력**: 지난 7일 일별 사용량 선 그래프 (점마다 kWh 라벨)

### 오른쪽 열
- **실내**: 거실/안방/내방/베란다 온도·습도
- **가족**: `[O]/[X] 이름 + 위치` (home 여부, 외출 시 Geocoded 주소)
- **Z.AI**: 토큰 잔여 % + 리셋 시간

### 하단 푸터
- `HA HH:MM` (갱신 기준 HA 시간)

---

## 변경 시 갱신 원리

- `run.py` `main()`이 매 `poll_interval`마다 프레임을 렌더링하고,
- SHA-256 해시가 **이전 프레임과 다를 때만** X4 `/upload` 로 푸시합니다.
- 내용이 같으면 `unchanged` 로그만 남기고 푸시하지 않습니다 (전자종이 고스팅·배터리 절약).

---

## 개발

### 로컬 구조

```
x4-ha-addon/
├── repository.yaml               # HAOS 애드온 저장소 정의
├── README.md                     # 이 문서
└── x4-dashboard/
    ├── config.yaml               # 애드온 옵션/스키마
    ├── Dockerfile                # 알파인 + python3 + tzdata
    └── run.py                    # 센서 수집 · 렌더링 · 푸시
```

### 시간대

Dockerfile에 `ENV TZ=Asia/Seoul` 과 `tzdata` 패키지를 넣습니다. **`tzdata`가 없으면** 알파인 이미지에 zone 정보가 없어서 `TZ` 설정이 무시되고 시각이 UTC(9시간 텀)로 표시됩니다. `run.py`에도 `os.environ.setdefault("TZ","Asia/Seoul")` + `time.tzset()` 이 들어 있습니다.

### 프레임 형식

- 크기: `800×480`, 1-bit, MSB-first, `0=black`, `1=white`
- 크기: 정확히 48,000 바이트 (`W*H/8`)

`run.py` 렌더링 후 `len(raw) == W*H//8` 를 `assert` 로 확인합니다.

---

## 로그 확인

시작 시: `vX.Y starting — X4=<ip> interval=<n>s`
정상 갱신: `pushed` / 내용 동일 시: `unchanged`

```
[19:49:01] v5.6 starting — X4=192.168.0.144 interval=60s
[19:49:03] pushed
[19:50:03] pushed
```

---

## 유의사항

- API 토큰(`ha_token`, `x4_token`), Wi-Fi 비밀번호, 개인 경로를 이 저장소에 커밋하지 마세요.
- 센서 엔티티 ID가 실제로 존재하는지 먼저 확인하세요 (없으면 `--` 로 표시).
- 초기 설치 후 HAOS가 이미지 캐시를 물고 있으면 이전 버전이 계속 뜰 수 있습니다. 캐시 우회는 slug 변경 또는 애드온 삭제→재설치로 처리합니다.

---

## 문서 링크

| 문서 | 내용 |
|---|---|
| [docs/ENTITIES.md](docs/ENTITIES.md) | 화면 영역별 사용 엔티티 목록 |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 버전 관리 · 배포 · 캐시 문제 해결 |
