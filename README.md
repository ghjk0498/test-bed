# Multi-Service Test Bed Infrastructure

이 프로젝트는 Docker Compose를 기반으로 다양한 백엔드 서비스(RabbitMQ, PostgreSQL 등)를 로컬 환경에 쉽게 구성하고 테스트하기 위한 다중 서비스 관리 환경입니다. 서비스 중심(Service-First) 아키텍처로 구성되어 있으며, 각 서비스별 독립적인 실행, 관리 스크립트 및 테스트 코드를 포함하고 있습니다.

## 🚀 프로젝트 구조 (Service-First Architecture)

- `src/rabbitmq/`: RabbitMQ 클러스터 상태 확인, 쿼럼 큐(Quorum Queue) 조작 및 페일오버 테스트 도구
- `src/postgres/`: PostgreSQL 데이터베이스 연결 검증 및 상태 진단 도구
- `src/core/`: 공통 유틸리티 및 전역 설정 로드 관련 모듈
- `config/`: `rabbitmq.conf` 등 각 서비스별 로컬 설정 파일
- `docs/`: 서비스 운영 런북(Runbook), 재해 복구(DR) 가이드 및 테스트 시나리오 등 문서

## 📋 사전 요구 사항

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Make](https://www.gnu.org/software/make/) (선택 사항, Windows의 경우 GnuWin32 Make 권장)

## 🛠️ 실행 및 관리 명령어

각 서비스는 독립적인 컨테이너와 스크립트로 동작합니다. 해당 서비스 디렉토리(`src/<서비스명>`)로 이동하여 `make` 명령어를 실행하십시오.

### RabbitMQ 클러스터 (3-Node)
```bash
cd src/rabbitmq
make up        # 클러스터 실행
make status    # 클러스터 상태 확인
make down      # 클러스터 종료
make clean     # 볼륨(데이터) 삭제
```

### PostgreSQL
```bash
cd src/postgres
make up        # 컨테이너 실행
make status    # DB 연결 확인
make down      # 컨테이너 종료
make clean     # 데이터 삭제
```

### 전체 코드 품질 및 검증 (루트 디렉토리)
```bash
make lint      # 전체 코드 포맷팅 및 린트
make test      # 전체 회귀 및 통합 테스트 실행
```

## 🌐 접속 정보 및 기본 설정

### RabbitMQ
- **Management UI**: `http://localhost:15672` (rabbit1), `15673` (rabbit2), `15674` (rabbit3)
- **계정**: `guest` / `guest`

### PostgreSQL
- **포트**: `5432`
- **DB명**: `testdb`
- **계정**: `admin` / `secret_pass`

> **참고**: 상세한 운영 방법 및 트러블슈팅 가이드는 `docs/` 하위의 각 서비스별 매뉴얼을 참조하십시오.
