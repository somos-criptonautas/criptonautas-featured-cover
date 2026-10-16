FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends libcairo2 fontconfig \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY assets/InterTight.ttf /usr/share/fonts/truetype/inter-tight/
# Fail the build if cairo would fall back to another face: the covers would come out wrong without an error.
RUN fc-cache -f && fc-match "Inter Tight" | grep -q InterTight
WORKDIR /app
COPY --chmod=0444 cover.py server.py ./
COPY --chmod=0444 assets/ ./assets/
USER 65534:65534
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "server.py"]
