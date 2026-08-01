FROM alpine:3.20

RUN apk add --no-cache python3 py3-pillow font-noto-cjk tzdata

WORKDIR /app
COPY run.py .

CMD ["python3", "/app/run.py"]
