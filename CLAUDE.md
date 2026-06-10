# TelematicsHub

## What this project does

Mini telematics integration pipeline built to demonstrate
skills for Shippeo (supply chain GPS data company).
Ingests real aircraft positions from OpenSky Network API
every 30s, detects anomalies, exposes a FastAPI REST API,
generates AI cycle summaries via Ollama (local).

## Stack

Python, FastAPI, SQLite, requests, schedule, ollama (local)

## File structure (planned)

- config.py — all constants and settings
- models.py — Position dataclass + raw vector parser
- database.py — SQLite schema + CRUD
- ingester.py — OpenSky fetch + normalize
- anomaly.py — 3 detectors (speed, stale, bounds)
- api.py — FastAPI routes
- ai_summary.py — Ollama cycle summary
- main.py — orchestration + scheduler

## Rules

- Show diff before modifying any existing file
- One module at a time, wait for my confirmation
- Explain what the code does before writing it
- Keep each file under one single responsibility
