dev:
	docker compose -f infra/compose/docker-compose.dev.yml up --build

down:
	docker compose -f infra/compose/docker-compose.dev.yml down

start-local:
	bash ./start-local.sh

api-local:
	python3 apps/api/run.py

api-test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s apps/api/tests -v

web-local:
	cd apps/web && npm run dev
