# RUN THE BACKEND

1. Install Pillow, fastapi, uvicorn, ultralytics
2. Create a virutal environment
3. Active the virtual environment
4. Run uvicorn main:app --reload --host 0.0.0.0 --port 8000

*Check http://127.0.0.1:8000/health.
*Need to have:

{
  "status": "ok",
  "message": "FastAPI server is running!"
}
