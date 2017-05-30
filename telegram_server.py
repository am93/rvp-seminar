import socket, threading, socketserver, time
import sys, getopt
from queue import Queue
from datetime import datetime

# global devices array
devices = []

class Device():
    def __init__(self, id, name, ip, port, sckt):
        self.id = id
        self.name = name
        self.ip = ip
        self.port = port
        self.sckt = sckt
        self.queue = Queue()
        self.last_sent = None
        self.last_ack = None


class TelegramSender(threading.Thread):
    def run(self):
        global devices
        while True:
            for d in devices:
                if d.name == 'Server':
                    continue #do nothing for now
                if d.sckt is not None and d.last_sent == d.last_ack and d.queue.qsize() > 0:
                    new_payload = d.queue.get(block=False)
                    d.sckt.sendall(bytes(new_payload, 'ascii'))
                    d.last_sent = new_payload
                    print('['+str(datetime.now())+'] Sending telegram -> '+d.name+': '+new_payload)
            time.sleep(0.05)


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        #global sockets
        #if sockets == None:
        #    sockets = self.request
        data = str(self.request.recv(1024), 'ascii')

        # if payload length is less then 5, then it must be new device connection
        if len(data) < 5:
            self.set_device_socket(self.client_address[0], self.request)
        else:
            print('['+str(datetime.now())+'] Received telegram: '+data)
            self.parse_payload(data, self.request)


    def set_device_socket(self, addr, request):
        global devices
        for d in devices:
            if addr == d.ip:
                d.sckt = request    # TODO: check if this modifies object instance
                print('Device '+d.ip+' connected...')
                return
        print('Received message from unknown device: '+addr)


    def parse_payload(self, payload, request):
        global devices
        new_telegram = payload[:int(len(payload)/2)]
        ack_telegram = payload[int(len(payload)/2):]
        # if telegram starts with four zeros it servers only as placeholder
        if not new_telegram[:4] == '0000':
            devices[int(new_telegram[1])].queue.put(new_telegram)
        # if last values is 1, we have ack telegram
        if ack_telegram[-1]:
            devices[int(new_telegram[1])].last_ack = ack_telegram[:-1:] + '0'


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def initialize():
    # globlas
    global devices

    # default settings
    host, port = "193.2.72.241", 2017
    line1, line2, robot = None, None, None

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'i:p:l1:l2:r:h', ['ip=', 'port=', 'line1=', 'line2=', 'robot=', 'help'])
    except getopt.GetoptError:
        print('Error during options parsing...')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-i', '--ip'):
            host = arg
        elif opt in ('-p', '--port'):
            port = int(arg)
        elif opt in ('-l1', '--line1'):
            line1 = arg
        elif opt in ('-l2', '--line2'):
            line2 = arg
        elif opt in ('-r', '--robot'):
            robot = arg
        else:
            print('Run script with following options:')
            print('-i,  --ip    : ip address of server (default: 193.2.72.241)')
            print('-p,  --port  : port to which server will bind (default: 2017)')
            print('-l1, --line1 : ip address of PLC for line 1 (default: None)')
            print('-l2, --line2 : ip address of PLC for line 2 (default: None)')
            print('-r,  --robot : ip address of PLC for robot hand (default: None')
            print('-h,  --help  : displays this help message')
            sys.exit(3)

    devices.append(Device(0, 'Server', host, port, None))  # server
    devices.append(Device(1, 'Line1', line1, None, None)) # line 1
    devices.append(Device(2, 'Line2', line2, None, None)) # line 2
    devices.append(Device(3, 'Robot', robot, None, None)) # robot hand

    return host, port


if __name__ == "__main__":
    # initialize server configuration
    HOST, PORT = initialize()

    # setup server
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    print("Server loop running on IP:",str(ip),", PORT:",str(port)," ...")

    # Start telegram sender thread
    tlg_thread = TelegramSender()
    tlg_thread.start()

    while True:
        time.sleep(0.1)
        #print(sockets)
        #if sockets is not None:
        #    sockets.sendall(bytes('hello12345', 'ascii'))

    server.shutdown()
    server.server_close()