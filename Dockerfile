FROM python:3.11-slim
COPY requirements.txt requirements.txt
RUN  pip install --upgrade pip  --no-cache-dir && pip install -r requirements.txt
WORKDIR /app
RUN mkdir probe
COPY . .
COPY mod/ mod/
EXPOSE 8080
CMD [ "python", "deadpool.py" ]