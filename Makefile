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
