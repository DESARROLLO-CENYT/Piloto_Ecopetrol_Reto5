"""Levanta el backend + frontend del piloto en http://127.0.0.1:8000

Uso:  .venv/Scripts/python.exe run_app.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", app_dir="app", host="127.0.0.1", port=8000, reload=False)
