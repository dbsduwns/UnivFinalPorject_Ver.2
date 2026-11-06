# KNU Campus 앱 업데이트 운영 가이드

## 최초 부트스트랩 APK

이 저장소의 `1.1.0` 버전부터 OTA 업데이트와 직접 배포 APK 업데이트를 지원합니다. 기존 APK에는 업데이트 모듈이 없으므로 사용자가 `1.1.0` APK를 한 번 직접 설치해야 합니다.

```powershell
eas build --profile preview --platform android
```

기존 설치본 위에 업데이트하려면 `com.yeojun.knu` 패키지 이름과 Android 서명키가 반드시 같아야 합니다. 동일한 EAS 프로젝트의 credentials를 계속 사용합니다.

## JavaScript·화면 OTA 업데이트

네이티브 모듈이나 Android 권한이 바뀌지 않은 변경은 채널별로 배포합니다.

```powershell
eas update --channel preview --message "변경 내용" --environment preview
eas update --channel production --message "변경 내용" --environment production
```

앱은 실행 시와 포그라운드 복귀 시 업데이트를 확인합니다. 새 OTA를 내려받으면 재시작 안내 모달을 표시합니다.

## 새 APK 릴리스

1. `app.json`의 `version`을 올립니다.
2. 동일한 EAS Android credentials로 APK를 빌드합니다.
3. APK를 Google Cloud Storage 등 HTTPS 다운로드 주소에 업로드합니다.
4. 백엔드 마이그레이션과 최신 API를 먼저 배포합니다.
5. 관리자 웹의 **서비스 데이터 → Android APK 버전 관리**에서 다음 값을 등록합니다.
   - 사용자에게 보이는 버전 이름
   - Android `versionCode`
   - 최소 지원 `versionCode`
   - APK HTTPS 주소
   - 릴리스 노트
   - 필수 업데이트 여부

활성 릴리스는 Android 플랫폼에서 하나만 유지됩니다. `minimum_version_code`보다 오래된 설치본과 `mandatory` 릴리스는 닫을 수 없는 업데이트 모달을 표시합니다.

## DB 마이그레이션

앱 릴리스 및 알림센터 테이블을 만들기 위해 API 배포 전에 실행합니다.

```powershell
python -m alembic upgrade head
```
