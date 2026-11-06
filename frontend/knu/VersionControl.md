# 애플리케이션 버전 관리 지침

## 1. 목적

이 문서는 KNU 애플리케이션의 버전 번호, Android APK 빌드 번호, EAS Update(OTA), 서버 배포를 일관되게 관리하기 위한 기준이다.

가장 중요한 원칙은 다음과 같다.

> 설치된 APK의 네이티브 실행 환경과 호환되는 변경은 같은 앱 버전으로 OTA 배포하고, 네이티브 실행 환경이 달라지는 변경은 앱 버전을 올린 뒤 새 APK를 빌드한다.

앱 버전은 모든 코드 배포마다 올리는 번호가 아니다. 사용자가 설치하는 APK와 그 APK가 수신할 수 있는 OTA 업데이트의 호환성 경계를 나타낸다.

## 2. 현재 프로젝트 기준 정보

| 항목 | 현재 값 | 역할 |
| --- | --- | --- |
| 앱 버전 (`version`) | `1.1.0` | 사용자에게 표시되는 버전이며 현재 `runtimeVersion`의 기준 |
| Android 빌드 번호 (`versionCode`) | `2` | Android가 APK의 신구 버전을 판단하는 정수 |
| 런타임 버전 (`runtimeVersion`) | `1.1.0` | 해당 APK가 받을 수 있는 OTA 업데이트의 호환성 키 |
| 런타임 정책 | `appVersion` | `version` 값을 `runtimeVersion`으로 사용 |
| Android 패키지 | `com.yeojun.knu` | 앱의 고유 식별자. 기존 앱 업데이트 시 변경 금지 |
| EAS 프로젝트 ID | `87e8b9ce-407e-4fb8-8537-b275ce8f6a0d` | EAS Build/Update 프로젝트 식별자 |
| 배포 APK 채널 | `preview` | 현재 직접 배포하는 APK가 구독하는 OTA 채널 |

실제 Expo 프로젝트 디렉터리는 `frontend/knu`이다. Expo 및 EAS 명령은 반드시 이 디렉터리에서 실행한다.

```powershell
cd D:\coding\YunGit\UnivFinalProject\Ver.2\frontend\knu
```

저장소 루트의 `app.json`은 실제 앱 설정 파일이 아니다. 버전과 EAS 설정은 반드시 `frontend/knu/app.json`에서 관리한다.

## 3. 각 버전 값의 의미

### 3.1 `version`

`frontend/knu/app.json`의 `expo.version` 값이다. `1.1.0`처럼 SemVer 형식을 사용한다.

현재 `runtimeVersion.policy`가 `appVersion`이므로 이 값을 바꾸면 OTA 호환 런타임도 함께 바뀐다.

- `version: 1.1.0`으로 발행한 OTA는 런타임 `1.1.0` APK만 받을 수 있다.
- `version: 1.2.0`으로 발행한 OTA는 기존 런타임 `1.1.0` APK가 받을 수 없다.
- 따라서 단순히 업데이트 이름을 `1.2.0`으로 표시하려는 목적으로 `version`만 먼저 올리면 안 된다.

### 3.2 `versionCode`

Android가 APK 업데이트 가능 여부를 판단하는 정수이다.

- 새 APK를 빌드할 때마다 반드시 증가해야 한다.
- 이전에 배포한 번호를 재사용하거나 더 낮은 번호로 되돌리면 안 된다.
- 현재 EAS의 `appVersionSource`는 `remote`, 빌드 프로필은 `autoIncrement`를 사용하므로 EAS가 증가시킨다.
- 빌드 완료 후 실제 `versionCode`를 확인하여 관리자 웹의 APK 버전 정보에 동일하게 입력한다.

`version`이 같더라도 새 APK를 배포한다면 `versionCode`는 달라야 한다. 다만 운영 혼선을 피하기 위해 네이티브 변경으로 APK를 새로 배포할 때는 원칙적으로 `version`도 함께 올린다.

### 3.3 `runtimeVersion`

설치된 네이티브 바이너리와 OTA JavaScript 번들의 호환성을 판단하는 값이다.

현재 정책에서는 앱 버전과 동일하다. `runtimeVersion`이 다른 OTA는 기기에 다운로드되어도 적용되지 않는다.

### 3.4 EAS Update 메시지

같은 앱 버전으로 여러 번 OTA를 발행할 때는 버전 번호 대신 업데이트 메시지로 배포 내용을 구분한다.

권장 형식은 다음과 같다.

```text
fix(notice): 공지 목록 새로고침 및 정렬 오류 수정
feat(notification): 알림센터 읽음 처리 개선
```

## 4. 같은 버전으로 배포하는 변경

다음 조건을 모두 만족하면 `app.json`의 `version`을 유지하고 EAS Update로 배포한다.

1. 변경 사항이 JavaScript/TypeScript 또는 OTA에 포함 가능한 에셋에만 존재한다.
2. 설치된 APK에 이미 필요한 네이티브 모듈과 권한이 들어 있다.
3. 기존 서버 API와 호환된다.
4. 데이터 손상이나 앱 실행 불가 위험이 없다.

대표 사례는 다음과 같다.

| 변경 사항 | 배포 방식 | 이유 |
| --- | --- | --- |
| React 컴포넌트, 화면 UI, 문구, 색상, 레이아웃 변경 | 같은 버전 OTA | JavaScript/스타일 변경 |
| 공지 정렬, 새로고침, 캐시 로직 수정 | 같은 버전 OTA | 앱 로직만 변경 |
| 알림센터 화면과 읽음 처리 로직 개선 | 같은 버전 OTA | 기존 네이티브 기능만 사용 |
| API 요청 파라미터 또는 응답 처리 수정 | 같은 버전 OTA | 서버가 이전 클라이언트와도 호환되는 경우 |
| 이미지, 폰트 등 번들 에셋 변경 | 같은 버전 OTA | 네이티브 아이콘/스플래시가 아닌 경우 |
| 순수 JavaScript 패키지 추가 또는 업데이트 | 같은 버전 OTA | 네이티브 코드가 포함되지 않은 경우 |
| 백엔드 버그 수정 또는 DB 인덱스 추가 | 앱 배포 불필요 | 클라이언트 API 계약이 유지되는 경우 |

기능의 크기가 크더라도 네이티브 런타임과 호환된다면 기술적으로는 같은 버전 OTA 배포가 가능하다. 다만 제품 정책상 사용자에게 `1.2.0` 같은 새 버전을 표시해야 한다면 새 APK 출시 절차를 밟아야 한다.

## 5. 앱 버전을 올리고 새 APK를 만들어야 하는 변경

다음 중 하나라도 해당하면 OTA만으로 배포하지 않고 `version`을 올린 후 새 APK를 빌드한다.

| 변경 사항 | 예시 |
| --- | --- |
| 네이티브 모듈 추가·제거·업데이트 | `expo-camera`, 지도 SDK, 결제 SDK, 네이티브 푸시 SDK 추가 |
| Expo SDK 또는 React Native 버전 변경 | Expo SDK 업그레이드 |
| 네이티브 플러그인 변경 | `app.json`의 `plugins` 추가·삭제·설정 변경 |
| Android 권한 변경 | 카메라, 위치, 저장소, APK 설치 권한 추가·삭제 |
| Android 네이티브 설정 변경 | 패키지명, intent filter, URL scheme, 딥링크 설정 |
| 앱 설치 리소스 변경 | 앱 아이콘, adaptive icon, 네이티브 splash 설정 |
| 네이티브 환경 설정 변경 | `google-services.json`, 네이티브 API 키, 빌드 속성 |
| 네이티브 계층 오류 수정 | APK 실행 전 크래시, 네이티브 모듈 충돌 수정 |
| 런타임 정책 변경 | `runtimeVersion` 정책 또는 값 변경 |
| 호환 불가능한 API 전환 | 기존 앱이 더 이상 서버와 정상 통신할 수 없는 변경 |

의존성 변경 시에는 패키지 이름만 보고 판단하지 말고 네이티브 코드 포함 여부를 확인한다. 순수 JavaScript 라이브러리는 OTA가 가능하지만, 네이티브 모듈을 연결하는 라이브러리는 새 APK가 필요하다.

## 6. SemVer 증가 기준

새 APK가 필요할 때 다음 기준으로 `MAJOR.MINOR.PATCH`를 정한다.

### PATCH: `1.1.0` → `1.1.1`

- 네이티브 버그 수정이나 의존성 패치 때문에 재빌드가 필요한 경우
- 기존 기능과 사용 방식은 유지되는 유지보수 출시
- 보안 패치 또는 빌드 설정 수정

### MINOR: `1.1.0` → `1.2.0`

- 하위 호환되는 새로운 사용자 기능을 새 APK로 출시하는 경우
- 새로운 네이티브 기능, 권한 또는 모듈을 추가하는 경우
- 제품 차원에서 구분할 필요가 있는 주요 기능 출시

### MAJOR: `1.2.0` → `2.0.0`

- 이전 앱·API·데이터 형식과의 호환성을 크게 깨는 경우
- 인증, 앱 구조 또는 핵심 사용 흐름을 전면 교체하는 경우
- 장기간 이전 버전을 병행 지원하기 어려운 대규모 전환

버전 증가 수준이 애매하면 다음 순서로 판단한다.

1. 기존 사용자가 사용 방법을 바꿔야 하는가?
2. 이전 클라이언트와 서버의 호환성이 깨지는가?
3. 새로운 네이티브 기능이 추가되는가?
4. 단순 유지보수인가?

## 7. 배포 결정 절차

```text
변경 사항 발생
  ├─ 네이티브 모듈·권한·플러그인·Expo SDK가 바뀌는가?
  │    ├─ 예 → 버전 증가 + 새 APK 빌드
  │    └─ 아니요
  ├─ 기존 앱과 서버 API 호환성이 깨지는가?
  │    ├─ 예 → 호환 API를 먼저 제공하거나 버전 증가 + 새 APK
  │    └─ 아니요
  ├─ 사용자에게 새 설치 버전으로 표시해야 하는 제품 출시인가?
  │    ├─ 예 → 버전 증가 + 새 APK 빌드
  │    └─ 아니요 → 현재 버전 유지 + EAS Update
```

## 8. 같은 버전 OTA 배포 절차

예를 들어 설치된 APK가 `version 1.1.0`, `runtimeVersion 1.1.0`, 채널 `preview`인 경우 다음 절차를 따른다.

1. 네이티브 변경이 없음을 확인한다.
2. `frontend/knu/app.json`의 `version`을 `1.1.0`으로 유지한다.
3. 타입 검사와 관련 테스트를 실행한다.
4. `frontend/knu`에서 preview 채널로 먼저 발행한다.

```powershell
cd D:\coding\YunGit\UnivFinalProject\Ver.2\frontend\knu
eas update --channel preview --message "fix(notice): 공지 새로고침 오류 수정" --environment preview
```

5. 실제 preview APK에서 업데이트 다운로드와 재시작 후 동작을 확인한다.
6. production APK가 별도로 배포된 이후에는 검증된 변경만 production 채널에 발행한다.

```powershell
eas update --channel production --message "fix(notice): 공지 새로고침 오류 수정" --environment production
```

OTA 롤백이 필요하면 EAS Dashboard 또는 현재 설치된 EAS CLI의 rollback 도움말을 사용한다. 롤백 대상 채널과 런타임을 반드시 확인한 후 실행한다.

## 9. 새 APK 배포 절차

1. 변경 성격에 맞게 SemVer를 결정한다.
2. `frontend/knu/app.json`의 `expo.version`을 수정한다.
3. 동일한 EAS 프로젝트와 서명 자격 증명을 사용해 APK를 빌드한다.

```powershell
cd D:\coding\YunGit\UnivFinalProject\Ver.2\frontend\knu
eas build --profile preview --platform android
```

4. EAS 빌드 결과에서 실제 `versionCode`와 사용된 채널을 기록한다.
5. 기존 APK 위에 새 APK를 설치해 정상 업데이트되는지 확인한다.
6. 로그인 정보, 로컬 데이터, 푸시 토큰이 유지되는지 확인한다.
7. APK를 HTTPS로 접근 가능한 배포 저장소에 업로드한다.
8. 필요한 백엔드 및 DB 마이그레이션을 먼저 배포한다.
9. 관리자 웹에서 Android APK 릴리스를 등록한다.

관리자 웹에 등록할 필수 정보는 다음과 같다.

- 버전명: 예) `1.2.0`
- versionCode: EAS 빌드 결과의 실제 값
- 최소 지원 versionCode
- APK HTTPS 다운로드 URL
- 릴리스 노트
- 필수 업데이트 여부

10. 일반 사용자의 다운로드, 설치 권한 안내, 설치 완료까지 전체 흐름을 검증한다.

세부 빌드 및 등록 과정은 [`frontend/knu/UPDATE_GUIDE.md`](frontend/knu/UPDATE_GUIDE.md)를 함께 참고한다.

## 10. 백엔드와 DB만 변경하는 경우

백엔드나 DB 변경만으로는 앱 버전을 올리지 않는다. 다만 기존에 설치된 앱과 API 호환성을 유지해야 한다.

호환성이 깨질 가능성이 있으면 다음과 같은 확장 후 축소 방식으로 배포한다.

1. 기존 필드와 새 필드를 함께 지원하는 백엔드 및 DB 변경을 먼저 배포한다.
2. 기존 앱이 계속 작동하는지 확인한다.
3. 새 클라이언트를 OTA 또는 APK로 배포한다.
4. 충분한 업데이트율과 안정성을 확인한다.
5. 마지막으로 오래된 API와 필드를 제거한다.

예를 들어 API 응답 필드명을 즉시 변경하지 말고 일정 기간 기존 필드와 새 필드를 동시에 제공한다.

## 11. 환경 변수 변경 기준

- `EXPO_PUBLIC_*` 값이 JavaScript에서만 사용되고 네이티브 설정에 영향을 주지 않으면 같은 버전 OTA가 가능하다.
- EAS Update 시 대상 환경에 맞는 `--environment preview` 또는 `--environment production`을 반드시 지정한다.
- 네이티브 플러그인, Android Manifest, Google 서비스 설정 등에 사용되는 값이 바뀌면 새 APK가 필요하다.
- 비밀키를 `EXPO_PUBLIC_*`에 저장하면 안 된다. 이 값은 앱 번들에 포함되어 사용자에게 노출될 수 있다.

## 12. 필수 업데이트 적용 기준

기본값은 선택적 업데이트로 한다. 다음과 같이 이전 버전의 계속 사용이 위험한 경우에만 필수 업데이트로 지정한다.

- 심각한 보안 취약점이 있는 경우
- 이전 버전이 데이터 손상이나 중복 처리를 일으키는 경우
- 인증 방식 변경으로 이전 버전이 정상 동작할 수 없는 경우
- 서버에서 이전 API 지원을 종료해야 하는 경우
- 앱 실행 또는 핵심 기능 사용이 불가능한 치명적 오류가 있는 경우

단순 UI 개선이나 일반 버그 수정에 필수 업데이트를 사용하지 않는다. `minVersionCode`는 실제로 차단해야 할 최소 범위를 확인한 후 보수적으로 설정한다.

## 13. 변경 사례별 판단 예시

| 사례 | 앱 버전 변경 | 배포 방식 |
| --- | --- | --- |
| 공지 목록의 `published_at` 정렬 수정 | 없음 | `1.1.0` OTA |
| Pull-to-refresh 로직 추가 | 없음 | `1.1.0` OTA |
| 알림센터 UI와 읽음 상태 처리 개선 | 없음 | `1.1.0` OTA |
| 알림 DB 인덱스 추가 | 없음 | 백엔드/DB만 배포 |
| 기존 API에 선택 필드 추가 | 없음 | 백엔드 배포 후 필요 시 OTA |
| API 필드를 제거하여 구버전 앱이 깨짐 | 필요 가능성 높음 | 호환 API 선배포 후 새 APK 검토 |
| 카메라 기능과 `expo-camera` 추가 | `1.2.0` 권장 | 새 APK |
| 앱 아이콘 또는 네이티브 splash 변경 | PATCH 또는 MINOR | 새 APK |
| Expo SDK 업그레이드 | PATCH 또는 MINOR | 새 APK |
| 문구 오탈자 수정 | 없음 | OTA |

## 14. 서명과 패키지 관리 규칙

- 기존 앱을 업데이트하려면 패키지명 `com.yeojun.knu`를 유지한다.
- 반드시 기존 APK와 동일한 Android 서명 키를 사용한다.
- EAS 자격 증명을 임의로 새로 만들거나 교체하지 않는다.
- 서명 키를 잃으면 기존 APK 위에 업데이트를 설치할 수 없다.
- 배포된 `versionCode`는 기록하고 재사용하지 않는다.
- APK 파일만 보관하지 말고 해당 소스 커밋, 버전, versionCode, EAS Build ID도 함께 기록한다.

권장 Git 태그 형식은 다음과 같다.

```text
android-v1.1.0-build2
android-v1.2.0-build3
```

OTA 배포는 Git 태그 대신 EAS Update 메시지와 커밋 해시를 릴리스 기록에 남긴다.

## 15. 배포 전 체크리스트

### OTA 배포

- [ ] 네이티브 모듈, 권한, 플러그인 변경이 없다.
- [ ] `frontend/knu/app.json`의 `version`을 변경하지 않았다.
- [ ] 대상 APK의 `runtimeVersion`과 OTA 런타임이 같다.
- [ ] 올바른 채널과 EAS 환경을 선택했다.
- [ ] API가 기존 앱과 하위 호환된다.
- [ ] preview APK에서 실제 업데이트를 검증했다.
- [ ] 업데이트 메시지에 변경 내용을 명확히 기록했다.

### 새 APK 배포

- [ ] SemVer 증가 수준을 결정했다.
- [ ] `frontend/knu/app.json`의 버전을 변경했다.
- [ ] EAS가 증가시킨 실제 `versionCode`를 확인했다.
- [ ] 패키지명과 Android 서명 키가 기존 APK와 같다.
- [ ] 기존 APK 위에 설치되는지 확인했다.
- [ ] 필요한 서버 및 DB 변경을 먼저 배포했다.
- [ ] APK를 HTTPS 주소에 업로드했다.
- [ ] 관리자 웹에 버전명, versionCode, URL, 릴리스 노트를 등록했다.
- [ ] 필수 업데이트 여부와 최소 지원 versionCode를 검토했다.

## 16. 핵심 금지 사항

1. 기존 `1.1.0` APK에 OTA를 보내면서 `app.json`만 `1.2.0`으로 올리지 않는다. 런타임이 달라져 기존 앱이 업데이트를 받지 못한다.
2. 저장소 루트에서 `eas update` 또는 `eas build`를 실행하지 않는다.
3. 새 APK의 `versionCode`를 이전 값과 같거나 더 낮게 만들지 않는다.
4. 패키지명 또는 서명 키를 출시 중간에 변경하지 않는다.
5. 구버전 앱과 호환되지 않는 서버 변경을 한 번에 배포하지 않는다.
6. 일반적인 기능 개선에 필수 업데이트를 남용하지 않는다.

