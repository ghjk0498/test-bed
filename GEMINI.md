# RabbitMQ Management Project Guide

이 프로젝트는 RabbitMQ 쿼럼 큐의 대량 생성 및 삭제 성능 최적화를 목표로 합니다. 모든 스크립트 작성 및 관리는 아래 가이드를 준수합니다.

## 1. 디렉토리 구조 표준
프로젝트는 다음과 같은 구조를 유지하며, **구조 변경 시 반드시 이 섹션을 업데이트해야 합니다.**

```text
E:\gemini-cli\RabbitMQ\
├── src/               # 구조화된 Python 소스 코드
│   ├── scripts/       # 실행 가능한 관리 스크립트 (예: manage_queues.py)
│   ├── utils/         # 재사용 가능한 유틸리티 (예: rabbitmq_api.py)
│   └── tests/         # 단위 테스트 및 검증 코드
├── Makefile           # 통합 명령어 인터페이스 (create/delete/lint 등)
├── docker-compose.yml # RabbitMQ 클러스터 인프라 정의
├── pyproject.toml     # Python 도구 설정 (Ruff, Mypy, Black, Pytest)
├── requirements.txt   # Python 라이브러리 의존성 목록
├── GEMINI.md          # 프로젝트 표준 가이드 및 구조 지도
└── rabbitmq.conf      # RabbitMQ 노드 설정 파일
```

- `src/utils/`: 공통 유틸리티 (API 호출, 인증 등)
- `src/scripts/`: 실제 실행 스크립트 (큐 생성, 삭제 등)
- `src/tests/`: 스크립트 검증을 위한 테스트 코드

## 2. Python 개발 표준
모든 Python 코드는 일관된 스타일과 품질을 유지하기 위해 다음 도구를 필수로 사용합니다.

### 코드 품질 및 포매팅
- **Black**: 코드 포매팅 표준 (Line length: 88)
- **Ruff**: Linting 및 자동 수정 (Select: E, F, I, N, S, UP)
  - `N`: PEP8 명명 규칙 준수
  - `S`: 보안 취약점 검사 (Bandit)
  - `UP`: 최신 Python 문법으로 업그레이드 제안
- **Mypy**: 정적 타입 검사 (Strict mode)

### 테스트 프레임워크
- **Pytest**: `src/tests/` 내의 테스트 코드를 실행하여 로직의 정확성을 검증합니다.

### 검사 워크플로우
스크립트 작성 또는 수정 후에는 반드시 아래 명령어를 순차적으로 수행하여 검증합니다.
```bash
# 1. 린트 및 자동 수정
ruff check . --fix

# 2. 정적 타입 검사
mypy .

# 3. 코드 포매팅
black .

# 4. 단위 테스트 실행
pytest
```

## 3. Makefile 통합
주요 작업은 `Makefile`을 통해 추상화합니다. 새로운 스크립트가 추가될 경우 `Makefile`에 타겟을 추가하여 일관된 인터페이스를 제공합니다.

## 4. 규칙
- 환경변수를 건드리지 말 것.
- lint 오류를 피하기 위해 검사를 무시하는 코드를 넣지 말 것.
