import os
import subprocess
import http.server
import socketserver

def main():
    print("Updating data...")
    subprocess.run(["python3", "export_data.py"])
    print("Data updated.")
    
    port = int(os.environ.get("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving at port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
