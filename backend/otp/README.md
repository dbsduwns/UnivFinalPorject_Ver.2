# OpenTripPlanner 로컬 검증

실제 서비스 환경을 기준으로 최신 OTP 2.10.0을 Docker로 실행한다.
호스트에 Java를 직접 설치하지 않고 컨테이너의 Java 25 런타임을 사용한다.

## 파일 배치

아래 파일을 `data` 디렉터리에 둔다.

```text
backend/otp/data/
├─ south-korea-latest.osm.pbf
└─ transit-gtfs.zip
```

`backend/otp/data/transit-gtfs.zip`은 KTDB에서 받은 GTFS 파일을 복사한 뒤 사용한다. 파일명에
`gtfs`가 포함되어야 OTP가 GTFS 입력으로 인식한다. KTDB 파일에서
`agency.txt`의 `agency_timezone` 값이 `Korea`라면 OTP 표준에 맞게 `Asia/Seoul`로
수정해야 할 수 있다.

## 그래프 생성

프로젝트 루트에서 실행한다.

```powershell
$otpDir = (Resolve-Path ".\backend\otp\data").Path

docker run --rm `
  -e JAVA_TOOL_OPTIONS='-Xmx12g' `
  -v "${otpDir}:/var/opentripplanner" `
  docker.io/opentripplanner/opentripplanner:2.10.0 `
  --build --save
```

첫 실행은 OSM과 GTFS를 읽어 `graph.obj`를 생성한다. 데이터가 크면 수 분 이상
걸릴 수 있다. 이후에는 다음처럼 기존 그래프를 불러온다.

```powershell
$otpDir = (Resolve-Path ".\backend\otp\data").Path

docker run -it --rm -p 8080:8080 `
  -e JAVA_TOOL_OPTIONS='-Xmx12g' `
  -v "${otpDir}:/var/opentripplanner" `
  docker.io/opentripplanner/opentripplanner:2.10.0 `
  --load --serve
```

## 샘플 경로 요청

서버가 실행된 뒤 다음 주소로 OTP 응답을 확인한다.

```text
http://localhost:8080/graphiql
```

OTP 2.10은 GraphQL API를 사용한다. 현재 데이터는 저장소에 포함하지 않는다. GTFS와 OSM 원본 및 OTP 그래프는 용량이
크므로 로컬에서만 관리한다.
