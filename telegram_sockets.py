import socket, threading, time
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


class ClientThread(threading.Thread):
    def __init__(self, channel, details):
        self.channel = channel
        self.details = details
        self.device_id = self.init_device(channel, details[0])
        self.channel.settimeout(1)
        threading.Thread.__init__(self)

    def init_device(self, sckt, rcv_ip):
        global devices
        for d in devices:
            if d.id == 0:
                continue # server
            if d.ip == rcv_ip and d.sckt is None:
                d.sckt = sckt
                print('Device ' + d.name + ' [' + d.ip + '] connected...')
                print(d.sckt)
                return d.id
            elif d.ip == rcv_ip and d.sckt is not None:
                d.sckt = sckt
                print('Device ' + d.name + ' [' + d.ip + '] reconnected...')
                return d.id
        print('Received message from unknown device: ' + rcv_ip)
        return -1

    def parse_payload(self, payload, recv_time):
        global devices
        new_telegram = payload[:int(len(payload) / 2)]
        ack_telegram = payload[int(len(payload) / 2):]
        # if telegram starts with four zeros it servers only as placeholder
        if not new_telegram[:4] == '0000':
            devices[int(new_telegram[1])].queue.put(new_telegram)
        # if last values is 1, we have ack telegram
        if int(ack_telegram[-1]):
            print('[' + recv_time + '] Telegram is ack: ' + payload)
            devices[int(ack_telegram[1])].last_ack = ack_telegram[:-1:] + '0'

    def sending_logic(self):
        global devices
        d = devices[self.device_id]
        if d.name == 'Server':
            return
        if d.sckt is not None and d.last_sent == d.last_ack and d.queue.qsize() > 0:
            new_payload = d.queue.get(block=False)
            self.channel.sendall(bytes(new_payload, 'ascii'))
            d.last_sent = new_payload
            print('[' + str(datetime.now()) + '] Sending telegram -> ' + d.name + ': ' + new_payload)

    def run(self):
        global devices
        # loop forever
        print('Device: ',self.device_id,' loop started...')
        payload = None
        recv_time = None
        while True:
            try:
                if payload is None:
                    payload = str(self.channel.recv(28), 'ascii')
                    recv_time = str(datetime.now())
            except socket.timeout:
                timeouted = True
            # try to parse recieved data
            if payload is not None:
                print('[' + recv_time + '] Received telegram: ' + payload)
                self.parse_payload(payload, recv_time)
                payload = None
                recv_time = None
            # try to send data
            self.sending_logic()


def initialize():
    # globals
    global devices

    # default settings
    host, port = "10.123.255.241", 2017
    line1, line2, robot = '10.123.20.79', None, '10.123.255.241'

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'i:p:l1:l2:r:h',
                                   ['ip=', 'port=', 'line1=', 'line2=', 'robot=', 'help'])
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
            print(opt)
            print('Run script with following options:')
            print('-i,  --ip    : ip address of server (default: 193.2.72.241)')
            print('-p,  --port  : port to which server will bind (default: 2017)')
            print('-l1, --line1 : ip address of PLC for line 1 (default: None)')
            print('-l2, --line2 : ip address of PLC for line 2 (default: None)')
            print('-r,  --robot : ip address of PLC for robot hand (default: None')
            print('-h,  --help  : displays this help message')
            sys.exit(3)

    devices.append(Device(0, 'Server', host, port, None))  # server
    devices.append(Device(1, 'Line1', line1, None, None))  # line 1
    devices.append(Device(2, 'Line2', line2, None, None))  # line 2
    devices.append(Device(3, 'Robot', robot, None, None))  # robot hand

    return host, port


if __name__ == "__main__":
    # initialize server configuration
    HOST, PORT = initialize()

    # setup server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    server.settimeout(1)

    print("Server loop running on IP:", str(HOST), ", PORT:", str(PORT), " ...")

    while True:
        try:
            channel, details = server.accept()
            ClientThread(channel, details).start()
        except socket.timeout:
            continue
