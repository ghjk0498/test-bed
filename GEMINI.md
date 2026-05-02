# Multi-Service Infrastructure Project Guide

이 프로젝트는 단일 환경에서 여러 서비스(RabbitMQ, PostgreSQL 등)의 자동화된 관리, 기능 검증, 장애 시뮬레이션 및 복구 환경을 체계적으로 구축하기 위한 다중 서비스(Multi-Service) 테스트베드입니다.

## 1. 디렉토리 구조 표준 (Service-First Architecture)
프로젝트는 서비스의 응집도를 높이기 위해 '역할별(scripts, utils)' 구조가 아닌 '서비스 중심(rabbitmq, postgres)' 구조를 유지합니다.

```text
E:\gemini-cli\test-bed\
├── docs/              # 서비스별 운영 매뉴얼 및 런북 (예: docs/rabbitmq/OPERATIONS_GUIDE.md)
├── src/               # 서비스 애플리케이션 및 인프라 구성 루트
│   ├── core/          # 서비스 공통 기반 유틸리티 및 테스트
│   ├── postgres/      # PostgreSQL 전용 관리 도구, docker-compose.yml, Makefile, 테스트
│   └── rabbitmq/      # RabbitMQ 전용 관리 도구, docker-compose.yml, Makefile, 테스트
├── Makefile           # 루트 수준 코드 린트 및 전체 테스트 명령
├── pyproject.toml     # Python 도구 설정 (Ruff, Mypy, Black, Pytest)
├── requirements.txt   # 의존성 목록
├── GEMINI.md          # 프로젝트 표준 가이드 (현재 파일)
└── README.md          # 프로젝트 사용법 개요
```

## 2. 개발 및 보안 표준

### Python 제약 사항
- **의존성 최소화**: 추가적인 서드파티 라이브러리(requests, sqlalchemy 등) 사용은 지양하고 가급적 Python 표준 라이브러리와 `subprocess`(docker exec)를 활용하여 외부 의존성을 낮춥니다.
- **보안 검사**: `subprocess.run` 사용 시 `S603` 린트 규칙을 준수하며 외부 입력을 엄격히 통제합니다.
- **모듈 응집도**: 한 서비스의 기능 추가 시, 관련 스크립트, 유틸리티, 테스트를 모두 해당 서비스 폴더(`src/{service}/`) 내에 작성합니다.

### 코드 품질 도구 (Strict Mode)
- **Black**: 코드 포매팅 (Line length: 88)
- **Ruff**: Linting 및 자동 수정 (Select: E, F, I, N, S, UP)
- **Mypy**: 엄격한 정적 타입 검사 (`strict: true`)
- **Pytest**: `src/` 전체를 순회하며 회귀 및 통합 테스트 수행

## 3. 운영 및 지속성 원칙

### 컨테이너 관리 (Independent Compose)
- 프로젝트 루트의 공통 `docker-compose.yml` 대신, 각 서비스 폴더(`src/{service}/docker-compose.yml`) 내에 독립적으로 컨테이너 구성을 관리합니다.
- 특정 서비스를 기동하려면 해당 폴더로 이동하여 `make up` 또는 `docker-compose up -d`를 실행합니다.

### Makefile 인터페이스
- `Makefile` 타겟은 서비스 폴더 내부에서 로컬하게 정의되어야 합니다 (예: `make up`, `make status`).
- Windows(PowerShell) 호환성을 위해 복잡한 셸 명령은 `@powershell -Command` 블록 내에서 작성합니다.

## 4. 핵심 규칙 (Core Mandates)
- **린트 우회 금지**: `# noqa` 또는 `type: ignore`는 명확한 이유 없이 남용하지 않습니다.
- **테스트 필수**: 기능을 수정하거나 추가할 경우 해당 서비스의 `tests/` 디렉토리에 단위 테스트를 추가하고 `make test`를 통과해야 합니다.
- **문서화 원칙**: 서비스의 핵심 설정이나 복구 절차가 변경되면, 관련된 `docs/` 디렉토리 하위의 마크다운 문서를 반드시 현행화합니다.
