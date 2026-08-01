# 배포 · 버전 관리 지침

HAOS의 "로컬 애드온" 캐시 문제(새 릴리스가 반영 안 되는 증상)를 피하기 위한 규칙을 정리합니다.

---

## 버전 관리 규칙

**변경할 때마다 `config.yaml`의 `version`을 올립니다.**

예: `5.6.0` 다음은 `5.7.0`. HAOS는 `config.yaml`의 `version` 필드와 파일 해시로 새 버전을 감지하므로
버전을 올리지 않으면 새 커밋을 푸시해도 업데이트가 뜨지 않습니다.

버전을 올릴 때 함께 맞춰줄 것 3곳:

1. `x4-dashboard/config.yaml` → `version: "X.Y.Z"`
2. `x4-dashboard/config.yaml` → `changelog:` (변경 요약)
3. `x4-dashboard/run.py` → `APP_VERSION` (화면 헤더 표시용)

`APP_VERSION`은 게시 펌웨어 버전(`v5.6`)과 동일하게 맞춥니다(화면 좌상단에 표시).

---

## 표준 커밋 흐름

```bash
cd <repo>
# 1) 수정
... 편집 ...

# 2) 로컬 검증
python3 -m py_compile x4-dashboard/run.py

# 3) 버전 확인
grep -n 'version:' x4-dashboard/config.yaml
grep -n 'APP_VERSION' x4-dashboard/run.py

# 4) 커밋·푸시
git add -A
git commit -m "vX.Y: <변경 요약>"
git push origin main
```

> 커밋 메시지 앞에 `vX.Y:` 형태를 권장해 git 히스토리에서 릴리스 단위를 식별하기 쉽게 합니다.

---

## 변경 후 HAOS 반영 확인

1. HAOS → 설정 → 애드온 → **X4 E-Paper Dashboard**
2. "최신 버전"이 올리려는 버전과 같은지 확인
3. 설치되어 있다면 **업데이트** / 없으면 설치
4. **시작** 후 로그에서 `vX.Y starting — X4=<ip>` 확인
5. 화면 헤더 `vX.Y` 표시 확인

---

## 캐시 문제 해결 (버전이 안 바뀌는 증상)

이 프로젝트에서 반복된 증상은 **코드는 push했는데 HAOS에서 여전히 이전 버전/이전 화면이 뜨는** 것입니다.
대부분 HAOS의 애드온 이미지 캐시가 원인입니다.

해결 순서(만든 조치 순):

1. **slug를 바꾼다** — 이 저장소는 `x4_dash` → `x4_paper`로 변경해 캐시를 우회했습니다.
   slug 변경은 사실상 "새 애드온" 취급이 되어 기존 캐시와 충돌하지 않습니다.
2. 기존 애드온 **삭제 후 재설치** — 이미지 캐시도 함께 재생성됩니다.
3. 캐시 문제가 계속되면 HAOS 자체를 재부팅하거나,
   Supervisor 설정에서 해당 앱의 Docker 이미지(`local_<slug>`)를 정리합니다.

---

## Dockerfile 기준

- 베이스: `alpine:3.20` (빌드 파라미터 `BUILD_FROM` 등 HAOS 주입값에 의존하지 않는 단순 구성)
- 패키지: `python3 py3-pillow font-noto-cjk tzdata`
  - `tzdata` 필수 — 없으면 `Asia/Seoul` zone 정보가 없어 UTC로 뜹니다.
- `ENV TZ=Asia/Seoul`
- `init: false`, `boot: auto`, `startup: application`
- `CMD`: `python3 /app/run.py` 직접 실행 (s6/run.sh 불필요)

> 주의: `config.yaml`에 `init: true`를 쓰면 HA의 s6 런타임 이미지가 필요해져 BUILD가 어려워집니다.
> `BUILD_FROM`으로 빈 베이스를 주입하는 방식은 로컬 빌드에서 실패했으므로 사용하지 않습니다.

---

## 이전에 실패한 구성 (회귀 방지)

- `FROM ${BUILD_FROM}` (빈 값 → base image name blank 오류)
- HA `base` + s6 + `run.sh` (`/run.sh: not found`, `/data/options.json`) — 서비스 초기화 복잡도 증가
- `/run.sh` CMD로 지정하면서 파일 누락

위 방식은 유지보수하지 마세요. 현재의 `alpine:3.20` + `init:false` + `CMD python3` 단일 구성으로 고정합니다.
