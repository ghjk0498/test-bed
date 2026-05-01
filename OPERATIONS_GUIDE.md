# RabbitMQ 운영 및 장애 대응 가이드 (Runbook)

이 가이드는 클러스터 이상 징후 발생 시 진단 방법과 조치 절차를 제공합니다. 로컬 테스트 환경과 원격 운영 환경 모두를 지원합니다.

---

## 0. 원격 운영 환경 설정 (Remote Setup)
운영 서버나 별도의 클러스터를 관리하려면 다음 환경 변수를 설정하십시오.

- **방법 (PowerShell)**:
  ```powershell
  $env:RMQ_HOST = "10.0.0.5"
  $env:RMQ_USER = "admin"
  $env:RMQ_PASSWORD = "yourpassword"
  ```
- **방법 (Linux/Bash)**:
  ```bash
  export RMQ_HOST=10.0.0.5
  export RMQ_USER=admin
  export RMQ_PASSWORD=yourpassword
  ```
- **실행**: 설정 후 `python src/scripts/manage_queues.py status`를 실행하여 연결을 확인합니다.

---

## 1. 정기 점검 및 모니터링
정상 상태를 유지하기 위해 다음 명령어로 클러스터 건강 상태를 수시로 확인합니다.

| 점검 항목 | 로컬/테스트 (Makefile) | 운영 환경 (직접 실행) |
| :--- | :--- | :--- |
| **클러스터 상태** | `make status` | `python src/scripts/manage_queues.py status` |
| **큐 안전성 요약** | `make queue-summary` | `python src/scripts/manage_queues.py queue-summary` |
| **리더 분산 확인** | `make dist` | `python src/scripts/manage_queues.py dist` |

---

## 2. 상황별 장애 대응 절차

### 상황 A: 특정 노드에 리더가 쏠려 있는 경우 (불균형)
- **조치**: 
  1. **로컬**: `make rebalance` 실행.
  2. **운영**: `python src/scripts/manage_queues.py rebalance` 실행.
  3. 분산 후 다시 `dist` 명령으로 결과를 확인합니다.

### 상황 B: 노드 장애 (Node Down) 발생 시
- **진단**: `status` 실행 시 특정 노드가 `Down`으로 표시됨.
- **조치**:
  1. **인프라 복구**:
     - **로컬**: `make start-node N=<노드번호>`
     - **운영**: 해당 서버 접속 후 `sudo systemctl start rabbitmq-server`
  2. **상태 확인**: 노드가 클러스터에 합류했는지 `status`로 확인합니다.
  3. **후속 조치**: 반드시 리더 리밸런싱(`rebalance`)을 수행합니다.

### 상황 C: 큐 복제본(Replica) 부족 (At Risk)
- **진단**: `queue-summary`에서 `At Risk` 경고 확인.
- **조치**:
  1. **멤버 추가**:
     - **로컬**: `make grow NODE=rabbit@<대상노드>`
     - **운영**: `python src/scripts/manage_queues.py grow --node rabbit@<대상노드>`
     - *(참고: 운영 환경은 RabbitMQ 3.13+ API가 필요합니다. 구버전은 서버에서 직접 CLI 실행)*

### 상황 D: 리소스 알람 (Memory/Disk Alarm)
- **진단**: `status`에서 특정 노드의 `Alarms`에 `Memory` 또는 `Disk` 표시.
- **조치**:
  1. **임시**: 컨슈머(Consumer) 수를 늘려 큐 적체를 해소합니다.
  2. **운영 서버**: `rabbitmqctl list_queues name memory` 등으로 메모리 점유가 높은 큐를 특정합니다.
  3. 알람 해제 후 퍼블리셔가 자동으로 `Blocked` 상태에서 풀리는지 확인합니다.

---

## 3. 예방을 위한 황금률 (Golden Rules)
1. **홀수 복제본 유지**: 쿼럼 큐는 항상 3, 5, 7개 등 홀수 복제본을 유지하십시오.
2. **복구 후 리밸런싱**: 노드 재시작이나 복구 후에는 반드시 `rebalance`를 수행하십시오.
3. **환경 변수 관리**: 운영 환경 접속 정보를 담은 `.env` 파일을 로컬에 저장할 경우 절대 Git에 커밋하지 마십시오.

---

## 4. 백업 및 복구 절차

### 4.1. 정의(Definitions) 백업 및 복구
- **로컬**: `make backup-defs FILE=backup.json`
- **운영**: `python src/scripts/manage_queues.py export-defs --file backup.json`

### 4.2. 전체 데이터(Full Data) 백업 및 복구
- **주의**: 이 작업은 컨테이너 또는 서비스를 일시 중지해야 합니다.
- **로컬**: `make backup-data` (볼륨 압축)
- **운영**: 
  1. 서비스 중지: `sudo systemctl stop rabbitmq-server`
  2. Mnesia 데이터 디렉토리(`/var/lib/rabbitmq/mnesia`) 백업.
  3. 서비스 재개: `sudo systemctl start rabbitmq-server`

---

## 5. 운영 서버 전용 진단 도구 (Production Diagnostics)

API로 확인되지 않는 깊은 문제는 운영 서버에 직접 접속하여 다음 도구를 사용하십시오.

### 5.1. 로그 확인 (Logs)
- **위치**: `/var/log/rabbitmq/rabbit@<hostname>.log`
- **실시간 확인**: `tail -f /var/log/rabbitmq/rabbit@<hostname>.log`
- **에러 집중 확인**: `grep "ERROR" /var/log/rabbitmq/rabbit@<hostname>.log`

### 5.2. 고급 진단 (Diagnostics)
- **클러스터 노드 간 연결 확인**: `sudo rabbitmq-diagnostics check_port_connectivity`
- **노드 리소스 상세 리포트**: `sudo rabbitmq-diagnostics observer` (또는 `top` 형식의 `sudo rabbitmq-diagnostics runtime_thread_stats`)
- **Erlang VM 상태 확인**: `sudo rabbitmq-diagnostics memory_breakdown`

### 5.3. 큐 리플리카 상세 진단
- **특정 큐의 상태 상세 조회**: `sudo rabbitmq-queues quorum_status <queue_name>`
  - 이 명령은 쿼럼 큐의 Raft 로그 상태, 컨센서스 참여 노드 정보를 상세히 보여줍니다.

---

## 부록: 운영 효율화 팁 (Efficiency Tips)

매번 긴 명령어를 입력하는 대신 다음 별칭(Alias) 설정을 권장합니다.

### Linux (Bash/Zsh)
`~/.bashrc` 또는 `~/.zshrc`에 추가:
```bash
# RabbitMQ 관리 도구 별칭
alias rmq='python3 /path/to/src/scripts/manage_queues.py'
alias rmq-status='rmq status'
alias rmq-test='rmq test-connection'
```

### Windows (PowerShell)
`$PROFILE`에 추가:
```powershell
function rmq { python src/scripts/manage_queues.py @args }
function rmq-status { rmq status }
```
