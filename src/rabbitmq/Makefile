# Makefile - RabbitMQ Cluster Environment

.PHONY: up down clean status rebalance dist queue-summary create delete stop-node start-node partition-node rejoin-node test

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
	@powershell -Command "if (Test-Path ./data) { Remove-Item -Recurse -Force ./data }"

status:
	python manage_queues.py status

rebalance:
	python manage_queues.py rebalance

dist:
	python manage_queues.py dist

queue-summary:
	python manage_queues.py queue-summary

# 쿼럼 큐 리더 리밸런싱 및 분포 확인
# 사용법: make create N=5
create:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 5 }; \
		python manage_queues.py create --n $$n"

delete:
	@powershell -Command "$$n = if ('$(N)') { $(N) } else { 5 }; \
		python manage_queues.py delete --n $$n"

# 장애 주입 (Fault Injection)
# 사용법: make stop-node N=2
stop-node:
	docker stop rabbit$(N)

start-node:
	docker start rabbit$(N)

partition-node:
	@powershell -Command "$$net = (docker network ls --filter name=rabbit-net --format '{{.Name}}'); \
		docker network disconnect $$net rabbit$(N)"

rejoin-node:
	@powershell -Command "$$net = (docker network ls --filter name=rabbit-net --format '{{.Name}}'); \
		docker network connect $$net rabbit$(N)"

test:
	pytest tests/
