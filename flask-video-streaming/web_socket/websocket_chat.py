# -*- coding:utf-8 -*-
# coding=utf-8


import threading
import hashlib
import socket
import base64
import struct

global clients
clients = {}


# 通知客户端
def notify(message):
    msg_bytes = stringTobytes(message)
    #msg_bytes = message
    for connection in clients.values():
        connection.send(msg_bytes)

def stringTobytes(message):
    # 发送websocket server报文部分
    msgLen = len(message)
    backMsgList = []
    backMsgList.append(struct.pack('B', 129))

    if msgLen <= 125:
        backMsgList.append(struct.pack('b', msgLen))
    elif msgLen <= 65535:
        backMsgList.append(struct.pack('b', 126))
        backMsgList.append(struct.pack('>h', msgLen))
    elif msgLen <= (2 ^ 64 - 1):
        backMsgList.append(struct.pack('b', 127))
        backMsgList.append(struct.pack('>h', msgLen))
    else:
        print("the message is too long to send in a time")
        return
    message_byte = bytes()
    print(type(backMsgList[0]))
    for c in backMsgList:
        # if type(c) != bytes:
        # print(bytes(c, encoding="utf8"))
        message_byte += c
    message_byte += bytes(message, encoding="utf8")
    # print("message_str : ", str(message_byte))
    # print("message_byte : ", bytes(message_str, encoding="utf8"))
    # print(message_str[0], message_str[4:])
    # self.connection.send(bytes("0x810x010x63", encoding="utf8"))
    # self.connection.send(message_byte)
    return message_byte


# 客户端处理线程
class websocket_thread(threading.Thread):
    def __init__(self, connection, username):
        super(websocket_thread, self).__init__()
        self.connection = connection
        self.username = username

    def run(self):
        print('new websocket client joined!')
        data = self.connection.recv(1024)
        headers = self.parse_headers(data)
        token = self.generate_token(headers['Sec-WebSocket-Key'])
        self.connection.send(b'HTTP/1.1 101 WebSocket Protocol Hybi-10\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n' % token)
        while True:
            try:
                data = self.connection.recv(1024)
            except socket.error:
                print("unexpected error: ")
                clients.pop(self.username)
                break

            data = self.parse_data(data)
            if len(data) == 0:
                continue
            message = self.username + ": " + data
            notify(message)


    def parse_data(self, msg):
        """
        客户端发送至server的websocket报文分为四部分：
        固定部分 ‘\x81’
        报文内容长度（”报文内容长度”）
        小于127， 填充8bit表示内容长度
        小于2^16-1, 填充第一个8bit为126的十六进制表示，后面16bit表示内容长度
        小于2^64-1, 填充第一个8bit为127的十六进制表示，后面64bit表示内容长度
        掩码mask
        mask由四字节组成
        报文内容content
        获得掩码mask和content,注意报文内容长度不同会影响mask和content在websocket报文中的起始位置
        :param msg: 
        :return: 
        """
        #v = ord(msg[1]) & 0x7f
        v = msg[1] & 0x7f
        # 0x7e 就是126，这种情况下，后面16bit表示内容长度
        # msg[0] 是0x81固定值，msg[1] 是0x00-0x7f之间的值
        # 这里的16bit也就是2个8bit，所以msg[2]和msg[3]是表达内容的长度的
        # 所以数据开始的位置是msg[4]开始，所以这里的p=4
        if v == 0x7e:
            p = 4
        # 0x7f 就是127，这种情况下，后面64bit表示内容长度
        # 和上面一样，8 * 8 = 64，所以p = 2+8 = 10
        elif v == 0x7f:
            p = 10
        else:
            p = 2
        mask = msg[p:p + 4]
        data = msg[p + 4:]
        res = ''.join([chr(v ^ mask[k % 4]) for k, v in enumerate(data)])
        print(res)
        return res

    def parse_headers(self, msg):
        """
        In python 3, bytes strings and unicodestrings are now two different types. 
        Since sockets are not aware of string encodings, they are using raw bytes strings, 
        that have a slightly differentinterface from unicode strings.
        So, now, whenever you have a unicode stringthat you need to use as a byte string, 
        you need toencode() it. And whenyou have a byte string, you need to decode it to use 
        it as a regular(python 2.x) string.

        Unicode strings are quotes enclosedstrings. Bytes strings are b”” enclosed strings
        When you use client_socket.send(data),replace it by client_socket.send(data.encode()). 
        When you get datausing data = client_socket.recv(512), 
        replace it by data =client_socket.recv(512).decode()
        :param msg: 
        :return: 
        """
        headers = {}
        if isinstance(msg, bytes):
            msg = msg.decode()
        header, data = msg.split('\r\n\r\n', 1)
        for line in header.split('\r\n')[1:]:
            key, value = line.split(': ', 1)
            headers[key] = value
        headers['data'] = data
        return headers

    def generate_token(self, msg):
        key = msg + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        key = key.encode()
        ser_key = hashlib.sha1(key).digest()
        return base64.b64encode(ser_key)


# 服务端
class websocket_server(threading.Thread):
    def __init__(self, port):
        super(websocket_server, self).__init__()
        self.port = port

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', self.port))
        sock.listen(5)
        print('websocket server started!')
        while True:
            connection, address = sock.accept()
            try:
                username = "ID" + str(address[1])
                thread = websocket_thread(connection, username)
                thread.start()
                clients[username] = connection
            except socket.timeout:
                print('websocket connection timeout!')


if __name__ == '__main__':
    server = websocket_server(9000)
    server.start()