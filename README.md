# m-accounting

Run the combined FastAPI + Dash app:

```bash
uv run uvicorn app.server:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000/api
- Dash: http://localhost:8000/dash/

Data is stored as JSON files under `./data/` by default. You can change the location later or switch to MongoDB.