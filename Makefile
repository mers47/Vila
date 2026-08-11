.PHONY: admin test lint

admin:
	@[ -n "$(ADMIN_EMAIL)" ] || (echo "ADMIN_EMAIL is required"; exit 1)
	@[ -n "$(ADMIN_PASSWORD)" ] || (echo "ADMIN_PASSWORD is required"; exit 1)
	docker compose run --rm api python scripts/create_admin.py "$(ADMIN_EMAIL)" "$(ADMIN_PASSWORD)"

test:
	docker compose run --rm test pytest -v

lint:
	docker compose run --rm api ruff check .

dev:
	docker compose up -d --build