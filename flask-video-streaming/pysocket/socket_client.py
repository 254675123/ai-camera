import socket
import os


def main():
    # 建立套接字
    tcp_socket = socket(socket.AF_INET, socket.SOCK_STREAM)
    # 接收用输入的服务器端的ip和端口
    tcp_ip = input("请输入ip:")

    tcp_port = int(input("请输入端口:"))
    # 连接服务器
    tcp_socket.connect((tcp_ip, tcp_port))
    # 输入要下载的文件名
    file_name = input("请输入要下载的文件名:")

    # 将文件名发送至服务器端
    tcp_socket.send(file_name.encode())
    # 创建一个空文件
    new_file = open(file_name, "wb")
    # 用与计算读取的字节数
    time = 0

    while True:
        # 接收服务器端返回的内容
        mes = tcp_socket.recv(4096)
        # 如果内容不为空执行
        if mes:
            # 解码并向文件内写入
            new_file.write(mes.decode())

            # 计算字节
            time += len(mes)

        else:
            # 如果字节数为空即未收到内容
            if time == 0:
                # 关闭文件
                new_file.close()
                # 删除刚刚创建的文件
                os.remove(file_name)
                print("没有您要下载的文件")
            else:
                # 如过time有值时name文件传输完成
                print("文件下载成功")

            break
    # 关闭套接字
    tcp_socket.close()


if __name__ == '__main__':
    main()
