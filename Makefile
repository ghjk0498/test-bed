# Makefile
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

status:
	python src/scripts/manage_queues.py status

clean:
	docker-compose down -v

# 쿼럼 큐 생성 최적화
# 사용법: make create N=100
create:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 5 }; \
		python src/scripts/manage_queues.py create --n $$n"

# 쿼럼 큐 삭제 최적화
# 사용법: make delete N=100
delete:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 5 }; \
		python src/scripts/manage_queues.py delete --n $$n"

# 쿼럼 큐 리더 리밸런싱
rebalance:
	python src/scripts/manage_queues.py rebalance

# 큐 리더 노드 분포 확인
dist:
	python src/scripts/manage_queues.py dist

# 개별 큐 상세 상태 확인
# 사용법: make queue-status N=10 (상위 10개 출력)
queue-status:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 10 }; \
		python src/scripts/manage_queues.py queue-status --n $$n"

# 큐 전체 요약 정보 확인
queue-summary:
	python src/scripts/manage_queues.py queue-summary

# 기존 타겟 유지 (하위 호환성)
create-queues: create
delete-queues: delete

# 장애 주입 (Fault Injection)
# 사용법: make stop-node N=2
stop-node:
	docker stop rabbit$(N)

start-node:
	docker start rabbit$(N)

restart-node:
	docker restart rabbit$(N)

# 네트워크 격리 (Partition) - 수동 네트워크 이름 찾기 포함
# PowerShell 환경 대응
partition-node:
	@powershell -Command "$$net = (docker network ls --filter name=rabbit-net --format '{{.Name}}'); \
		docker network disconnect $$net rabbit$(N)"

rejoin-node:
	@powershell -Command "$$net = (docker network ls --filter name=rabbit-net --format '{{.Name}}'); \
		docker network connect $$net rabbit$(N)"

# 쿼럼 큐 멤버 일괄 추가 (Grow)
# 사용법: make grow NODE=rabbit@rabbit2
grow:
	python src/scripts/manage_queues.py grow --node $(NODE)

# 쿼럼 큐 멤버 일괄 제거 (Shrink)
# 사용법: make shrink NODE=rabbit@rabbit2
shrink:
	python src/scripts/manage_queues.py shrink --node $(NODE)

# 코드 품질 검사
lint:
	ruff check . --fix
	mypy .
	black .
	pytest

# 백업 및 복구 (Definitions)
# 사용법: make backup-defs FILE=my_defs.json
backup-defs:
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'definitions_backup.json' }; \
		python src/scripts/manage_queues.py export-defs --file $$f"

# 사용법: make restore-defs FILE=my_defs.json
restore-defs:
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'definitions_backup.json' }; \
		python src/scripts/manage_queues.py import-defs --file $$f"

# 백업 및 복구 (Data - Full Volume)
# 주의: 이 작업은 컨테이너를 일시 중지합니다.
# 사용법: make backup-data FILE=backup.zip
backup-data:
	docker-compose stop
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'rabbitmq_data_backup.zip' }; \
		if (Test-Path $$f) { Remove-Item $$f }; \
		Compress-Archive -Path ./data -DestinationPath $$f; \
		Write-Host 'Data backup completed: ' $$f"
	docker-compose start

# 사용법: make restore-data FILE=backup.zip
restore-data:
	docker-compose down
	@powershell -Command "$$f = if ('$(FILE)') { '$(FILE)' } else { 'rabbitmq_data_backup.zip' }; \
		if (!(Test-Path $$f)) { Write-Error 'Backup file not found'; exit 1 }; \
		if (Test-Path ./data) { Remove-Item -Recurse -Force ./data }; \
		Expand-Archive -Path $$f -DestinationPath .; \
		Write-Host 'Data restored from ' $$f"
	docker-compose up -d
