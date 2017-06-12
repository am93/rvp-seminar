import time
import socket
import threading

class ClientThread(threading.Thread):
    def __init__(self, channel, details):
        self.channel = channel
        self.details = details
        threading.Thread.__init__ ( self )

    def run(self):
        send_counter = 0
        print('Received connection:', self.details[0])
        time.sleep(30)
        request = self.channel.recv(1024)
        while send_counter < 5:
            send_counter += 1
            self.channel.sendall(request)
            time.sleep(20)
        self.channel.close()
        print('Closed connection:', self.details[0])

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('10.123.255.241', 2017))
server.listen(5)
server.settimeout(1)

while True:
    try:
        channel, details = server.accept()
        ClientThread(channel, details).start()
    except socket.timeout:
        continue