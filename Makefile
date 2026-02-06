.PHONY: all install run setup api clean help

# Variables
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

all: help

help:
	@echo "Meeting Assistant - Management Commands"
	@echo "---------------------------------------"
	@echo "make install  - Create venv and install dependencies"
	@echo "make run      - Start recording (CLI)"
	@echo "make setup    - Run interactive audio device setup"
	@echo "make api      - Start Web API server"
	@echo "make clean    - Remove virtual environment and temporary files"

$(VENV)/bin/activate: requirements.txt
	@echo "[*] Creating virtual environment..."
	python3 -m venv $(VENV)
	@echo "[*] Installing dependencies (this may take a few minutes for PyObjC)..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate

install: $(VENV)/bin/activate
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			echo "[*] Creating .env from .env.example..."; \
			cp .env.example .env; \
		else \
			echo "[*] .env.example not found. Creating a blank .env..."; \
			echo "DEEPGRAM_API_KEY=" > .env; \
			echo "GEMINI_API_KEY=" >> .env; \
		fi; \
		echo "[!] Please edit .env and add your API keys!"; \
	fi
	@echo "[+] Installation complete."

run: install
	@$(PYTHON) main.py

setup: install
	@$(PYTHON) main.py --setup

api: install
	@$(PYTHON) api.py

clean:
	@echo "[*] Cleaning up..."
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf core/__pycache__
	rm -rf core/recorders/__pycache__
	rm -rf core/utils/__pycache__
	rm -rf .pytest_cache
	@echo "[+] Cleanup complete."
