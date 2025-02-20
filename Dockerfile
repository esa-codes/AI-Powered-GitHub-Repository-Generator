FROM python:3.11-slim-buster

WORKDIR /app

# Aggiorna l'indice dei pacchetti e installa git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia tutti i file Python
COPY *.py .

# Copia le directory templates e static
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 5000

CMD ["python", "app.py"]
