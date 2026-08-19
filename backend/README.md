# RUN THE BACKEND

1. Create a virutal environment
2. Active the virtual environment
3. Run python -m pip install --upgrade pip
       python -m pip install --no-cache-dir -r requirements.txt
4. Run uvicorn main:app --reload --host 0.0.0.0 --port 8000

* If have Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit), mean that run successful