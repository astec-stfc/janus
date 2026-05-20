FROM python:3.12-slim

RUN apt-get update && apt-get install procps ffmpeg libsm6 libxext6 curl -y

RUN python -m pip install pydantic p4p requests pyyaml --no-cache-dir

COPY . src/app

WORKDIR src/app

# CMD ["tail", "-f", "/dev/null"]
CMD ["python", "main.py"]