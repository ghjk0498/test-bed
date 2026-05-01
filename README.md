# RabbitMQ 3-Node Cluster (Docker)

이 프로젝트는 Docker Compose를 사용하여 **RabbitMQ 3.9.13** 버전의 3개 노드 클러스터를 자동으로 구축하는 스크립트를 제공합니다.

## 🚀 주요 기능
- **자동 클러스터링**: `rabbitmq.conf` 설정을 통해 노드 기동 시 자동 클러스터 구성
- **Management UI**: 모든 노드에 Management 플러그인 활성화
- **간편한 관리**: Makefile을 통한 원클릭 생성 및 삭제

## 📋 사전 요구 사항
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Make](https://www.gnu.org/software/make/) (선택 사항, 직접 docker 명령어 사용 가능)
```bash
winget install GnuWin32.Make
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files (x86)\GnuWin32\bin", "User")
```

## 🛠️ 실행 및 관리 명령어

### 1. 클러스터 시작
```bash
make up
```
- 모든 컨테이너를 백그라운드에서 실행하고 약 10초 대기 후 클러스터 상태를 표시합니다.

### 2. 클러스터 상태 확인
```bash
make status
```
- 현재 클러스터링된 노드 목록과 상태를 확인합니다.

### 3. 클러스터 종료
```bash
make down
```
- 실행 중인 컨테이너를 정지하고 제거합니다.

### 4. 전체 삭제 (데이터 초기화)
```bash
make clean
```
- 컨테이너와 함께 생성된 모든 볼륨(데이터)을 완전히 삭제합니다.

## 🌐 접속 정보 (Management UI)

| 노드 이름 | 호스트 포트 | 관리 UI 주소 |
| :--- | :--- | :--- |
| **rabbit1** | 15672 | [http://localhost:15672](http://localhost:15672) |
| **rabbit2** | 15673 | [http://localhost:15673](http://localhost:15673) |
| **rabbit3** | 15674 | [http://localhost:15674](http://localhost:15674) |

- **기본 계정**: `guest` / `guest`
- **AMQP 포트**: 5672(rabbit1), 5673(rabbit2), 5674(rabbit3)

## ⚙️ 주요 설정 파일
- `docker-compose.yml`: 서비스 정의 및 Erlang Cookie 설정
- `rabbitmq.conf`: 피어 검색(Peer Discovery) 및 노드 목록 설정
- `Makefile`: 명령어 자동화 스크립트
