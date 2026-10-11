# Lumen task runner. On Windows (no make), use the identical `pnpm <task>` scripts
# in package.json — e.g. `pnpm dev`, `pnpm test`, `pnpm gen:api`.
.PHONY: dev down logs build test seed simulate gen-api api-test web-typecheck

dev:            ## boot the whole stack (postgres, redis, minio, api, worker, scheduler, web)
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

build:
	docker compose build

test: api-test  ## pytest (api) [+ web tests land in M13]
	@echo "web test suite (vitest/Playwright) is added in M13"

api-test:
	cd api && ./venv/Scripts/python.exe -m pytest -q

web-typecheck:
	cd web && pnpm typecheck

seed:           ## load seed/*.json + demo account (implemented in M2)
	docker compose exec api python -m app.cli seed

simulate:       ## run the delivery simulator for HOURS (implemented in M8): make simulate HOURS=24
	docker compose exec api python -m app.cli simulate --hours $(HOURS)

gen-api:        ## regenerate web/src/lib/api from the running API's OpenAPI
	cd web && pnpm gen:api
