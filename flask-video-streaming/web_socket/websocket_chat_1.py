import socket
import base64
import hashlib
import re
import threading
import struct


HOST = "localhost"
PORT = 8080
MAGIC_STRING = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
HANDSHAKE_STRING = "HTTP/1.1 101 Switching Protocols\r\n" \
      "Upgrade:websocket\r\n" \
      "Connection: Upgrade\r\n" \
      "Sec-WebSocket-Accept: {1}\r\n" \
      "WebSocket-Location: ws://{2}/chat\r\n" \
      "WebSocket-Protocol:chat\r\n\r\n"


def recv_data(clientSocket):
    try:
        info = clientSocket.recv(2048)
        if not info:
            return
    except:
        return
    else:
        print(info)
        code_len = info[1] & 0x7f
        if code_len == 0x7e:
            extend_payload_len = info[2:4]
            mask = info[4:8]
            decoded = info[8:]
        elif code_len == 0x7f:
            extend_payload_len = info[2:10]
            mask = info[10:14]
            decoded = info[14:]
        else:
            extend_payload_len = None
            mask = info[2:6]
            decoded = info[6:]
        bytes_list = bytearray()
        print(mask)
        print(decoded)
        for i in range(len(decoded)):
            chunk = decoded[i] ^ mask[i % 4]
            bytes_list.append(chunk)
        raw_str = str(bytes_list, encoding="utf-8")
        print(raw_str)


def send_data(clientSocket):
    data = "need to send messages中文"
    token = b'\x81'
    length = len(data.encode())
    if length<=125:
        token += struct.pack('B', length)
    elif length <= 0xFFFF:
        token += struct.pack('!BH', 126, length)
    else:
        token += struct.pack('!BQ', 127, length)
    data = token + data.encode()
    clientSocket.send(data)



def handshake(serverSocket):
    while True:
        # print("getting connection")
        clientSocket, addressInfo = serverSocket.accept()
        # print("get connected")
        request = clientSocket.recv(2048)
        print(request.decode())
        # 获取Sec-WebSocket-Key
        ret = re.search(r"Sec-WebSocket-Key: (.*==)", str(request.decode()))
        if ret:
            key = ret.group(1)
        else:
            return
        Sec_WebSocket_Key = key + MAGIC_STRING
        # print("key ", Sec_WebSocket_Key)
        # 将Sec-WebSocket-Key先进行sha1加密,转成二进制后在使用base64加密
        response_key = base64.b64encode(hashlib.sha1(bytes(Sec_WebSocket_Key, encoding="utf8")).digest())
        response_key_str = str(response_key)
        response_key_str = response_key_str[2:30]
        # print(response_key_str)
        # 构建websocket返回数据
        response = HANDSHAKE_STRING.replace("{1}", response_key_str).replace("{2}", HOST + ":" + str(PORT))
        clientSocket.send(response.encode())
        # print("send the hand shake data")
        t1 = threading.Thread(target = recv_data, args = (clientSocket,))
        t1.start()
        t2 = threading.Thread(target = send_data, args = (clientSocket,))
        t2.start()


def main():
    # 创建基于tcp的服务器
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    host = (HOST, PORT)
    serverSocket.bind(host)
    serverSocket.listen(128)
    print("服务器运行, 等待用户链接")
    # 调用监听
    handshake(serverSocket)


if __name__ == "__main__":
    main()