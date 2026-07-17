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

# Placeholder entrypoint until the pipeline (scrape -> link -> classify ->
# commit) exists. Replace once slice 1 (Amnesty scraper) lands.
CMD ["python", "-c", "print('hr-response-tracker: pipeline not implemented yet')"]
