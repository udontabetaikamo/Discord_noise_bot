# Use official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
# Cloud Run sets the PORT env var (usually 8080)
ENV PORT=8080
EXPOSE 8080

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Define environment variable
# ENV NAME World

# Run entrypoint.sh when the container launches
CMD ["./entrypoint.sh"]
