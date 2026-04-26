import socket

def probe_rtsp(host, port):
    print(f"Probing RTSP on {host}:{port}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((host, port))
        # Изпращаме OPTIONS заявка - това е стандартния начин да попитаме сървъра какво поддържа
        msg = "OPTIONS rtsp://{host}:{port}/ RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: RTSP-Probe\r\n\r\n".format(host=host, port=port)
        s.send(msg.encode())
        response = s.recv(1024).decode()
        print("\n--- SERVER RESPONSE ---")
        print(response)
        s.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe_rtsp("192.168.0.113", 554)
