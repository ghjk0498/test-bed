# Implementation Plan: Production Environment Support

## Overview
이 계획은 RabbitMQ 관리 스크립트 및 가이드(`OPERATIONS_GUIDE.md`)를 확장하여, 로컬 도커 환경뿐만 아니라 실제 운영(Production) 환경에서도 안전하고 효율적으로 동작하도록 개선하는 것을 목표로 합니다. 주요 초점은 원격 연결 보안(TLS), 생산성 향상을 위한 가시성 확보, 그리고 운영 환경 전용 워크플로우의 구체화입니다.

## Architecture Decisions
- **TLS 지원**: 운영 환경은 보안을 위해 HTTPS(15671)를 사용할 가능성이 높으므로, `urllib` 기반 클라이언트에 SSL/TLS 지원을 추가합니다.
- **API 중심 설계**: `docker exec`와 같은 로컬 의존성을 제거하고, 가능한 모든 정보를 RabbitMQ Management API를 통해 수집합니다.
- **환경 변수 우선 순위**: `RMQ_` 접두사를 가진 환경 변수를 통해 설정을 관리하며, `.env` 파일 지원을 검토합니다.

## Task List

### Phase 1: 연결 보안 및 검증 (Connectivity & Security)
- [x] **Task 1: SSL/TLS 연결 지원**
    - `RabbitMQClient` 및 `manage_queues.py`에서 `https://` 프로토콜 및 인증서 검증 옵션 추가.
    - **AC**: `RMQ_USE_SSL=true` 설정 시 `https`로 요청을 보냄.
- [x] **Task 2: 연결 테스트 명령어 (`test-connection`) 추가**
    - 단순히 API를 호출해보는 것을 넘어, 유저 권한(Admin 여부), 버전 호환성(3.13+), 클러스터 노드 접근 가능 여부를 리포트.
    - **AC**: `python src/scripts/manage_queues.py test-connection` 실행 시 요약 보고서 출력.

### Checkpoint: Foundation
- [x] 원격 HTTPS 클러스터에 연결 가능 여부 확인.
- [x] 린트 및 타입 검사 통과.

### Phase 2: 운영 가시성 강화 (Production Visibility)
- [x] **Task 3: 상세 노드 상태 정보 (`node-details`) 확장**
    - `status` 명령에서 CPU 사용률, 파일 디스크립터 사용량, 메모리/디스크 워터마크 정보를 추가.
    - **AC**: 운영 서버의 리소스 압박 상황을 스크립트만으로 정확히 파악 가능.
- [x] **Task 4: 알람(Alarms) 모니터링 및 이력 요약**
    - 현재 발생 중인 알람뿐만 아니라, 클러스터 전체의 경고 상태를 한눈에 볼 수 있는 요약 제공.
    - **AC**: `status` 출력 시 알람이 있는 노드를 강조 표시.

### Phase 3: 운영 가이드 최적화 (Operational Guide Update)
- [x] **Task 5: `OPERATIONS_GUIDE.md` 원격 전용 섹션 보강**
    - `systemctl` 기반 관리, 로그 확인 방법, `rabbitmq-diagnostics` 연동 가이드 추가.
    - **AC**: 도커 없이도 운영 가이드만 보고 장애 대응 가능.
- [x] **Task 6: 생산성 도구 (Shell Wrappers/Aliases) 제안**
    - 매번 긴 명령어를 입력하지 않도록 `alias` 설정 가이드 또는 간단한 래퍼 스크립트 제공.
    - **AC**: 운영 환경에서의 명령어 입력 횟수 단축.

### Checkpoint: Complete
- [x] 모든 `Makefile` 타겟이 원격 환경에서 동작 확인.
- [x] 운영 가이드가 실제 워크플로우와 일치함.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| API 버전 불일치 | High | `test-connection` 단계에서 버전 체크 및 기능 제한 알림 |
| 네트워크 지연(Latency) | Med | API 호출 타임아웃 설정 및 병렬 처리 최적화 |
| 보안 (비밀번호 노출) | High | 환경 변수 사용 권장 및 로그에서 민감 정보 마스킹 |

## Open Questions
- 운영 환경에서 특정 API 엔드포인트가 방화벽으로 막혀 있을 경우의 대체 방안은?
- `urllib` 대신 `requests` 라이브러리 도입 필요성 (현재는 Zero Dependency 유지 중)?
