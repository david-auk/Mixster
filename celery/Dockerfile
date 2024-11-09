# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir Celery redis

# Entry point for running the Celery worker
CMD ["celery", "-A", "celery", "worker", "--loglevel=info"]