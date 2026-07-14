.PHONY: help server-install server-api server-run server-setup server-check infra-up infra-down clean

SERVER_DIR := apps/server
SERVER_VENV := $(SERVER_DIR)/.venv
SERVER_PYTHON := $(SERVER_VENV)/bin/python3
SERVER_PIP := $(SERVER_VENV)/bin/pip

help:
	@echo "Meeting Assistant monorepo"
	@echo "  make server-install  Install Python dependencies"
	@echo "  make server-api      Start the FastAPI service"
	@echo "  make server-run      Run the legacy macOS CLI"
	@echo "  make server-setup    Configure the legacy recorder"
	@echo "  make server-check    Compile-check Python sources"
	@echo "  make infra-up        Start the API with Docker Compose"
	@echo "  make infra-down      Stop Docker Compose services"

$(SERVER_VENV)/bin/activate: $(SERVER_DIR)/requirements.txt
	python3 -m venv $(SERVER_VENV)
	$(SERVER_PIP) install --upgrade pip
	$(SERVER_PIP) install -r $(SERVER_DIR)/requirements.txt
	@touch $(SERVER_VENV)/bin/activate

server-install: $(SERVER_VENV)/bin/activate
	@if [ ! -f $(SERVER_DIR)/.env ] && [ -f $(SERVER_DIR)/.env.example ]; then cp $(SERVER_DIR)/.env.example $(SERVER_DIR)/.env; fi

server-api: server-install
	@cd $(SERVER_DIR) && .venv/bin/python3 api.py

server-run: server-install
	@cd $(SERVER_DIR) && .venv/bin/python3 main.py

server-setup: server-install
	@cd $(SERVER_DIR) && .venv/bin/python3 main.py --setup

server-check:
	@python3 -m compileall -q $(SERVER_DIR)

infra-up:
	docker compose -f infra/compose.yaml up --build

infra-down:
	docker compose -f infra/compose.yaml down

clean:
	rm -rf $(SERVER_VENV) $(SERVER_DIR)/__pycache__ $(SERVER_DIR)/core/**/__pycache__
