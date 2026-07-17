# Slim, pinned base image. This is the only supported way to run the
# pipeline, in CI and locally — see CONTRIBUTING.md.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements
# change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then bring in the rest of the project.
COPY . .

# Runs the combined event-ingestion pipeline (Amnesty + HRW, deduplicated --
# the only pipeline stages that exist so far). Replace with the full
# scrape -> link -> classify -> commit pipeline as later slices land.
CMD ["python", "-m", "scrapers.pipeline"]
