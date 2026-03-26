import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Worker is healthy")

def run_health_check_server():
    port = int(os.environ.get("PORT", 7860))
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print(f"Starting health check server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    # Start health check server in a separate thread
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    # Start Celery worker in the foreground
    print("Starting Celery worker...")
    subprocess.run([
        "celery", 
        "-A", "worker.celery_app", 
        "worker", 
        "--loglevel=info",
        "--concurrency=1" # HF Spaces (free) have limited CPU, better to be safe
    ])
