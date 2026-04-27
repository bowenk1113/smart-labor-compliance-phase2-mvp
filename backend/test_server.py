"""
测试服务器，验证环境是否可以运行
"""
import http.server
import socketserver
import json

class TestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "message": "企业用工与社保合规智能平台 API",
                "version": "1.0.0",
                "status": "running"
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "healthy"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode('utf-8'))

def run_server():
    PORT = 8000
    with socketserver.TCPServer(("0.0.0.0", PORT), TestHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}/")
        print(f"Health check: http://localhost:{PORT}/health")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()