# Makefile - RabbitMQ Cluster Management & Infrastructure

# ==============================================================================
# LOCAL INFRASTRUCTURE (Docker Based)
# 이 섹션의 명령은 로컬 도커 환경에서만 동작합니다.
# ==============================================================================
.PHONY: up down status clean create delete rebalance dist lint

up:
	docker-compose up -d
	@echo "Waiting for containers to stabilize (3s)..."
	@powershell -Command "Start-Sleep -s 3"
	@echo "Waiting for RabbitMQ applications to start..."
	docker exec rabbit1 rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit@rabbit1.pid
	docker exec rabbit2 rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit@rabbit2.pid
	docker exec rabbit3 rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit@rabbit3.pid
	@echo "All nodes are ready. Checking cluster status..."
	docker exec rabbit1 rabbitmqctl cluster_status

down:
	docker-compose down

clean:
	docker-compose down -v

# 장애 주입 (Fault Injection)
# 사용법: make stop-node N=2
stop-node:
	docker stop rabbit$(N)

start-node:
	docker start rabbit$(N)

restart-node:
	docker restart rabbit$(N)

# 네트워크 격리 (Partition)
partition-node:
	@powershell -Command "$$net = (docker network ls --filter name=rabbit-net --format '{{.Name}}'); \
		docker network disconnect $$net rabbit$(N)"

rejoin-node:
	@powershell -Command "$$net = (docker network ls --filter name=rabbit-net --format '{{.Name}}'); \
		docker network connect $$net rabbit$(N)"

# 백업 및 복구 (Data - Full Volume)
# 주의: 이 작업은 컨테이너를 일시 중지하며 로컬 볼륨 데이터를 대상으로 합니다.
backup-data:
	docker-compose stop
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'rabbitmq_data_backup.zip' }; \
		if (Test-Path $$f) { Remove-Item $$f }; \
		Compress-Archive -Path ./data -DestinationPath $$f; \
		Write-Host 'Data backup completed: ' $$f"
	docker-compose start

restore-data:
	docker-compose down
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'rabbitmq_data_backup.zip' }; \
		if (!(Test-Path $$f)) { Write-Error 'Backup file not found'; exit 1 }; \
		if (Test-Path ./data) { Remove-Item -Recurse -Force ./data }; \
		Expand-Archive -Path $$f -DestinationPath .; \
		Write-Host 'Data restored from ' $$f"
	docker-compose up -d

# ==============================================================================
# CLUSTER MANAGEMENT (API Based)
# 이 섹션의 명령은 환경 변수(RMQ_HOST, RMQ_USER 등)를 통해 원격 클러스터 관리도 가능합니다.
# 기본값은 localhost:15672 (guest/guest)입니다.
# ==============================================================================

status:
	python src/scripts/manage_queues.py status

# 쿼럼 큐 생성/삭제 최적화
create:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 5 }; \
		python src/scripts/manage_queues.py create --n $$n"

delete:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 5 }; \
		python src/scripts/manage_queues.py delete --n $$n"

# 쿼럼 큐 리더 리밸런싱 및 분포 확인
rebalance:
	python src/scripts/manage_queues.py rebalance

dist:
	python src/scripts/manage_queues.py dist

# 큐 상태 및 요약
queue-status:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 10 }; \
		python src/scripts/manage_queues.py queue-status --n $$n"

queue-summary:
	python src/scripts/manage_queues.py queue-summary

# 쿼럼 큐 멤버 관리 (Grow/Shrink)
# 원격 환경은 RabbitMQ 3.13+ API가 필요합니다.
grow:
	python src/scripts/manage_queues.py grow --node $(NODE)

shrink:
	python src/scripts/manage_queues.py shrink --node $(NODE)

# 백업 및 복구 (Definitions)
backup-defs:
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'definitions_backup.json' }; \
		python src/scripts/manage_queues.py export-defs --file $$f"

restore-defs:
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'definitions_backup.json' }; \
		python src/scripts/manage_queues.py import-defs --file $$f"

# 코드 품질 및 하위 호환성
lint:
	ruff check . --fix
	mypy .
	black .
	pytest

create-queues: create
delete-queues: delete
