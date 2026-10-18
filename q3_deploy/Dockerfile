# TODO: image for YOUR api service (compose service name: api).
# Expectations: python:3.12-slim or similar; install requirements.txt;
# copy q1_api/ in; serve app.main:app on port 8000.
# The compose build context is the REPO ROOT, so COPY paths start from there.
FROM python:3.10-slim
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY q1_api ./q1_api

CMD ["uvicorn", "app.main:app", "--app-dir", "q1_api", "--host", "0.0.0.0", "--port", "8000"]
