import socket

COMMON_PATHS = [
    "/", "/live", "/stream1", "/stream2", "/ch0", "/ch0_0", "/ch0_1",
    "/live.sdp", "/video", "/media/video1", "/onvif/device_service",
    "/cam/realmonitor?channel=1&subtype=0", # Dahua
    "/Streaming/Channels/101", # Hikvision
    "/h264", "/av0", "/av1"
]

def probe_path(host, port, path):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, port))
        msg = f"DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 2\r\nUser-Agent: VLC\r\n\r\n"
        s.send(msg.encode())
        resp = s.recv(1024).decode()
        s.close()
        if "200 OK" in resp:
            return "SUCCESS"
        elif "401 Unauthorized" in resp:
            return "AUTH REQUIRED"
        else:
            return resp.split('\n')[0]
    except:
        return "ERROR"

if __name__ == "__main__":
    host = "192.168.0.113"
    port = 554
    print(f"Probing common RTSP paths on {host}:{port}...")
    for path in COMMON_PATHS:
        res = probe_path(host, port, path)
        if res != "ERROR":
            print(f"Path {path:<30} -> {res}")
