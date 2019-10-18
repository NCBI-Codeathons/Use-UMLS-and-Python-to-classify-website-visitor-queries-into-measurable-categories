FROM python:3.7.2-slim

ENV TINI_VERSION v0.18.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]

WORKDIR /opt/app

COPY . /opt/app

RUN pip install -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:8080", "backend:app"]
