# RabbitMQ Management & Disaster Recovery Project Guide

이 프로젝트는 RabbitMQ 클러스터의 관리 자동화, 장애 시뮬레이션(Fault Injection), 그리고 재해 복구(DR) 환경 구축을 목표로 합니다. 모든 작업은 아래 가이드를 엄격히 준수합니다.

## 1. 디렉토리 구조 표준
프로젝트는 다음과 같은 구조를 유지하며, 구조 변경 시 이 섹션을 최신 상태로 유지해야 합니다.

```text
E:\gemini-cli\RabbitMQ\
├── data/              # 노드별 영구 데이터 저장소 (rabbit1, rabbit2, rabbit3)
├── src/               # 구조화된 Python 소스 코드
│   ├── scripts/       # 실행 스크립트 (큐 관리, 백업/복구, 장애 주입 등)
│   ├── utils/         # 재사용 가능한 유틸리티 (HTTP API, 공통 로직)
│   └── tests/         # 단위 및 통합 테스트 코드
├── Makefile           # 통합 명령 인터페이스 (Win32/PowerShell 호환)
├── docker-compose.yml # 3-노드 클러스터 및 볼륨 구성 정의
├── rabbitmq.conf      # 클러스터 노드 공통 설정
├── OPERATIONS_GUIDE.md # 운영 매뉴얼 및 트러블슈팅 런북
├── TEST_PLAN.md       # 장애 시뮬레이션 및 검증 시나리오
├── pyproject.toml     # Python 도구 설정 (Ruff, Mypy, Black, Pytest)
├── requirements.txt   # 최소 의존성 목록
├── GEMINI.md          # 프로젝트 표준 가이드 (현재 파일)
└── README.md          # 프로젝트 개요
```

## 2. 개발 및 보안 표준

### Python 제약 사항
- **의존성 최소화**: 외부 라이브러리(requests 등) 사용을 금지하며, `urllib.request`를 사용한 표준 라이브러리 기반의 HTTP 통신을 지향합니다.
- **보안 검사**: `subprocess.run` 사용 시 항상 출력을 캡처하고, `S603` 린트 오류를 피하기 위해 명령 인자를 엄격히 검증합니다. URL 호출 시 프로토콜(`http`, `https`)을 반드시 검사합니다.
- **오류 처리**: RabbitMQ CLI는 논리적 실패 시에도 종료 코드 0을 반환할 수 있으므로, 항상 `stdout/stderr`에서 `error`, `failed`, `invalid` 등의 키워드를 분석하여 성공 여부를 판단합니다.

### 코드 품질 도구 (Strict Mode)
- **Black**: 코드 포매팅 (Line length: 88)
- **Ruff**: Linting 및 자동 수정 (Select: E, F, I, N, S, UP)
- **Mypy**: 엄격한 정적 타입 검사 (`strict: true`)
- **Pytest**: 기능 검증 및 회귀 테스트

## 3. 운영 및 지속성 원칙

### 클러스터 영속성
- **노드 이름 고정**: `rabbit@rabbit1` 등의 노드 이름은 변경하지 않습니다. 이는 쿼럼 큐(Quorum Queue)가 복구 후 Raft 로그를 식별하는 데 필수적입니다.
- **데이터 백업**: 클러스터 전체 백업(`make backup-data`)은 `./data` 디렉토리 전체를 대상으로 하며, 복구 시 모든 노드의 상태를 동기화합니다.

### Makefile 인터페이스 (Win32 호환)
- 모든 `Makefile` 타겟은 `powershell -Command`를 사용하여 Windows 환경에서 일관되게 동작해야 합니다.
- 주요 명령군:
  - **Management**: `make status`, `make rebalance`, `make check-safety`
  - **Fault Injection**: `make stop-node`, `make partition-node`
  - **Disaster Recovery**: `make backup-defs`, `make backup-data`

## 4. 핵심 규칙 (Core Mandates)
- **환경 변수 보존**: 컨테이너 및 시스템 환경 변수를 임의로 수정하지 마십시오.
- **린트 우회 금지**: `# noqa` 또는 `type: ignore`는 보안 상의 이유나 기술적 한계가 명확한 경우에만 최소한으로 사용합니다.
- **검증 필수**: 모든 코드 수정 후에는 `Makefile`을 통해 린트, 타입 검사, 테스트를 순차적으로 실행하여 무결성을 확인합니다.
- **문서화**: 새로운 기능을 추가하거나 운영 절차를 변경할 경우 `OPERATIONS_GUIDE.md`를 즉시 업데이트합니다.
