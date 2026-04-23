import subprocess
import webbrowser
import time
import http.server
import socketserver
import os

def main():
    print("=" * 50)
    print("🚀 [1/3] 正在抓取最新歷史指數資料... (這可能需要幾秒鐘)")
    print("=" * 50)
    
    # 執行資料更新程式
    subprocess.run(["python3", "export_data.py"])
    
    print("\n" + "=" * 50)
    print("✅ [2/3] 資料更新完成！")
    print("=" * 50 + "\n")
    
    PORT = 8000
    
    # 找尋可用的 port 避免衝突
    while True:
        try:
            Handler = http.server.SimpleHTTPRequestHandler
            httpd = socketserver.TCPServer(("", PORT), Handler)
            break
        except OSError:
            PORT += 1

    url = f"http://localhost:{PORT}"
    
    print(f"🚀 [3/3] 正在啟動本地伺服器並開啟網頁...")
    print(f"👉 您的專案網址: {url}")
    print("💡 提示: 若要關閉伺服器，請按 Ctrl+C")
    
    # 等待一秒確保伺服器穩定啟動後再開啟瀏覽器
    time.sleep(1)
    webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已關閉。")
        httpd.server_close()

if __name__ == "__main__":
    main()
