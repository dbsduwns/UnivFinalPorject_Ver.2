# 등교 경로와 실시간 조회 분리

## 요청 흐름

- 홈 `CampusRouteCard` 버튼 → `GET /api/commute/today` → Google Routes 후보 경로 조회.
- 이 단계에서는 공공 API로 정류장·도착시간·차량 위치를 조회하지 않는다. 실시간 정보 기반 다음 버스 자동 교체도 하지 않는다.
- 지도는 홈과 사용자별 TanStack Query 캐시를 공유한다. 60초 이내 결과는 추가 경로 계산 없이 사용한다.
- 지도 경로 상세의 정류장 목록을 펼칠 때만 `POST /api/commute/transit-live`를 호출한다.
- 동시에 한 구간만 펼친다. 목록을 접거나 시트를 최소화하거나 다른 탭으로 이동하거나 앱을 백그라운드로 보내면 주기적 조회가 중지된다. 이미 서버에서 실행 중인 외부 요청까지 취소하는 것은 아니다.
- 새 경로/다른 사용자의 경로는 별도 키로 취급한다. 설정 저장의 `['commute', 'today']` 접두사 무효화는 유지한다.

## 외부 호출 절감

| 대상 | 캐시/재조회 정책 |
| --- | --- |
| Google 경로 후보 | 서버 60초, 동일 출발·도착·시간 요청 병합. 출발 시각 키는 분 단위 |
| 노선 검색·정류장·Google 구간과 공공 노선 연결 | 6시간 |
| 실시간 도착정보 및 차량 위치 | 기본 30초 |
| 정상 응답이지만 도착 예정 없음 | 120초 |
| 제공기관 오류 | 60초; 같은 기관 서비스의 연쇄 호출도 일시 중단 |
| 미지원·미설정·구간 연결 실패 | 자동 폴링 중지 |

동시에 들어온 같은 요청은 한 번만 실행하고 나머지는 결과를 공유한다. 캐시는 개수 제한을 두며 응답은 복제하여 사용자별 계산이 다른 요청의 결과를 변경하지 않게 한다. 네트워크 자동 재시도는 사용하지 않는다. 실시간 조회 시각을 화면에 표시한다.

### 제공기관별 동작

- 서울: 노선 검색·정류장 조회 후 노선 전체 도착정보 한 번으로 해당 정류장의 다음 차량을 선택한다. 도착 응답의 차량 ID와 구간 순서를 사용하므로 별도 차량 위치 API 호출이 없다.
- 경기: GBIS v2 노선·정류장 조회 후 `routeId + stationId + staOrder`로 도착정보를 받는다. 첫 차량의 남은 정류장 수로 현재 정류장 순서를 표현하므로 별도 차량 위치 API 호출이 없다.
- TAGO: 서울/경기 직접 연동이 설정되지 않았거나 노선이 매칭되지 않으면 지원 지역에 한해 사용한다. 도착 예정이 있을 때만 차량 위치도 조회한다. 위치 조회 실패 시 도착시간은 유지한다.
- 같은 번호의 다른 노선/반대 방향을 피하기 위해 탑승·하차 정류장의 이름/좌표와 순서를 검증한다. 불확실한 매칭은 표시하지 않는다.
- 차량 표시는 **정류장 순서 기반**이며 정확한 GPS 위치를 뜻하지 않는다. TAGO는 도착 응답에 차량 ID가 없어 ETA와 위치의 동일 차량 여부를 보장하지 않는다.
- 인천 BIS 직접 연동과 지하철 실시간 어댑터는 이번 변경에 포함하지 않았다. TAGO 미지원 구간 및 지하철은 Google 예정 정보로 안내하며 수도권 전체 실시간 지원을 보장하지 않는다.

## 설정/운영

실제 비밀 값은 변경하지 않았다. `.env.example`과 `.env.cloudrun.example`을 참고한다.

- `GOOGLE_MAPS_SERVER_API_KEY`: 기존 경로 예상 키.
- `PUBLIC_API_KEY`: 기존 TAGO 키. 선택적으로 `TAGO_BUS_API_KEY`가 있으면 우선한다.
- `SEOUL_BUS_API_KEY`: 서울 버스 노선정보·도착정보 활용 신청 후 설정.
- `GYEONGGI_BUS_API_KEY`: 경기도 버스 노선조회·도착정보 v2 활용 신청 후 설정.
- 공공데이터포털 키 문자열이 같아도 각 서비스의 활용 승인은 별도로 필요하다. 미설정 기관에는 요청하지 않는다.
- `SEOUL_BUS_DAILY_LIMIT`, `GYEONGGI_BUS_DAILY_LIMIT`, `TAGO_BUS_DAILY_LIMIT`: **프로세스·서비스별 자체 안전 상한**. 기본 900/900/9000회는 실제 승인 한도를 조회한 값이 아니므로 계정에 승인된 양과 다른 소비자의 사용량에 맞춰 낮춰야 한다.

캐시와 사용량 카운터는 메모리에만 존재한다. 재시작하면 초기화되고 Cloud Run의 여러 인스턴스/워커 사이에서 공유되지 않는다. 따라서 일일 총량 보장이나 다중 인스턴스 중복 요청 제거를 제공하지 않는다. 여러 인스턴스로 운영하려면 Redis 등 공유 캐시·분산 잠금·공유 일일 카운터가 필요하다. 이 변경은 배포 설정을 수정하지 않는다.

기존 `/live-buses` 엔드포인트는 호환성을 위해 남겼지만 새 지도 화면에서는 사용하지 않는다. 예전 앱은 기존 호출 정책을 사용하므로 새 프론트와 백엔드를 함께 배포해야 한다.

### Cloud Run 노선 연결 진단

`/api/commute/transit-live`는 노선 연결에 실패하면 HTTP 200과 `status=unmatched`를 반환한다. HTTP 성공 여부만으로 실시간 연결 성공을 판단하지 않는다. Cloud Run 로그에서 `transit_route_unmatched`를 검색하면 한 요청의 실패 원인이 JSON 한 줄로 기록된다. 인증키와 정확한 좌표는 로그에 포함하지 않는다.

- `api_key_not_configured`: 해당 제공기관용 환경변수가 없어 건너뜀
- `route_not_found`: API 검색 결과에서 Google 노선명과 정확히 일치하는 노선이 없음
- `too_many_route_candidates`: 같은 번호의 후보가 너무 많아 안전하게 특정하지 못함
- `departure_stop_not_found`, `arrival_stop_not_found`: 정류장명 또는 50m 이내 좌표 후보가 없음
- `departure_coordinate_mismatch`, `arrival_coordinate_mismatch`: 이름은 같지만 두 데이터의 좌표 차이가 200m를 초과함
- `direction_order_mismatch`: 두 정류장은 찾았지만 공공 노선 순서에서 도착 정류장이 출발 정류장 뒤에 있지 않음
- `ambiguous_stop_pair`, `ambiguous_route_candidates`: 정류장 쌍 또는 노선을 하나로 특정하지 못함
- `no_route_contains_requested_segment`: 해당 제공기관의 후보들을 검사했지만 일치 구간이 없음

현재 방향 판정은 `출발 정류장 순번 < 도착 정류장 순번`을 사용한다. Google의 `headsign`은 진단 로그에는 기록되지만 아직 매칭 조건으로 사용하지 않는다.

## 검증

외부 API 과금을 발생시키지 않는 모의 응답 테스트:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_commute_transit.py tests/test_transit_live.py -q
```

경로 예상에서 공공 API 호출이 없는지, 동일 요청 병합/캐시 만료, 서울·경기·TAGO 응답 변환, JSON/XML, 도착정보 없음과 API 오류 구분, 일일 자체 상한, 위치 API 실패 시 도착시간 유지 등을 확인한다. 실제 계정 권한·노선별 제공 범위는 배포 환경에서 별도로 확인해야 한다.

앱 확인 순서: 홈 계산 → 경로보기(60초 내 같은 경로 재사용) → 상세 목록 펼치기(실시간 시작) → 접기/시트 최소화/탭 이동/백그라운드(추가 폴링 없음).

## API 계약 참고

- [서울 버스 노선정보](https://www.data.go.kr/data/15000193/openapi.do)
- [서울 버스 도착정보](https://www.data.go.kr/data/15000314/openapi.do)
- [GBIS 노선조회 v2](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRoute)
- [GBIS 경유 정류장 v2](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRouteStation)
- [GBIS 도착정보 v2](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival)
