FROM python:3.11-slim
WORKDIR /app
COPY requirement.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirement.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
