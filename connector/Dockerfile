# BibleChat connector (MCP server) as a public web service.
# Build from the project folder:  docker build -f connector/Dockerfile -t biblechat-connector .
# Run:                            docker run -p 8000:8000 biblechat-connector   ->  http://localhost:8000/mcp
FROM python:3.12-slim
WORKDIR /app
COPY bibleask /app/bibleask
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /app/
ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "bibleask.mcp_server", "--http"]
