# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Update package list, enable contrib repository, and install the fonts
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    && apt-get update && apt-get install -y \
    fontconfig \
    && apt-get install -y --no-install-recommends \
    wget \
    cabextract \
    xfonts-utils \
    && wget -O /tmp/arial32.exe https://sourceforge.net/projects/corefonts/files/the%20fonts/final/arial32.exe \
    && cabextract /tmp/arial32.exe -d /usr/share/fonts/truetype/msttcorefonts \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Clean up
RUN rm -rf /tmp/arial32.exe

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5050 available to the world outside this container
EXPOSE 5050

RUN mkdir -p "/data/playlist"

RUN useradd -ms /bin/bash nonrootuser
RUN mkdir -p "/data/playlist" && chown nonrootuser /data/playlist

VOLUME /data

# Demote to non root lever
USER nonrootuser

# Define environment variable
ENV FLASK_APP=app.py

# Run the application
#CMD ["waitress-serve", "--port=5050", "--call", "app:create_app"]
CMD ["flask", "run", "--host=0.0.0.0", "--port=5050"]