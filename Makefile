.PHONY: install run test clean

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	ollama pull llama3

run:
	.venv/bin/uvicorn api:app --reload

test:
	.venv/bin/pytest tests/ -v

clean:
	rm -rf .venv __pycache__ telematicshub.db
