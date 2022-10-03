import sys
import select
import socket
import queue
import time
import re
import os

#Takes an IP address as an input and returns true if it is a valid ip address.  Does not verify if IP address is active
#
#@param ip: an IP address to be validated
#@returns: true if it is a valid ip address
def validate_ip(ip: str) -> bool:
    octets = ip.split('.')
    if (len(octets) != 4):
        print("\033[1;31m[ERROR]\033[1;0m: Invalid IP Address: IP address must be a 4 octect IPV4 address")
        return False
    for octet in octets:
        try: 
            x = int(octet)
            if  x < 0 or x > 255:
                print("\033[1;31m[ERROR]\033[1;0m: Invalid IP Address: Octets must be between 0 and 255")
                return False
        except:
            print("\033[1;31m[ERROR]\033[1;0m: Invalid IP Address: Octects must only contain integers")
            return False  
    print("\033[1;32m[LOG]\033[1;0m: IP Address Successfully Validated")
    return True


#Take a port number as an input and validates whether it is a valid port number
#
#@param port: The port to be validated
#@returns: true if it is a valid port number
def validate_port(port: str) -> bool:
    try:
        x = int(port)
    except: 
        print("\033[1;31m[ERROR]\033[1;0m: Port number must be an integer")
        return False
    if(x < 0 or x > 65535):
        print("\033[1;31m[ERROR]\033[1;0m: Port number must be between 0 and 65535")
        return False
    print("\033[1;32m[LOG]\033[1;0m: Port Successfully Validated")
    return True


# Starts a new server on the specified IP and Port and listens for incoming connections
#
#@param port: The port to listen on
#@param IP: The IP to listen on
def create_server(ip, port) -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(0)
    try:
        server.bind((ip, int(port)))
    except socket.error as err:
        print("\033[1;31m[ERROR]\033[1;0m: Server failed to bind at {}:{}, Error code: {}".format(ip, port, err))
        return None
    print("\033[1;32m[LOG]\033[1;0m: Server bound successfully at {}:{}, Beginning listener".format(ip, port))
    server.listen(5)
    return server


# Takes a new connection and processes it, closing when the connection is closed
#
#@param: Server: The server to process the request from
def process_new_readable_connection(s, connection, address, inputs, outputs):
    id = os.fork()
    message = ""
    if id != 0:
        return False
    second = time.time()
    while time.time() < second + 30:
        msg = None
        try:
            msg = connection.recv(1024).decode()
        except:
            pass

        if msg:
            print("msg exists")
            message += msg
            print(msg[-5:-1])
            if msg[-9:-1] == "\r\n\r\n" or msg[-3:-1] == "\n\n":
                #deal with the message, move to persistant if it has keep alive and otherwise close connection
                print("msg format correct")
                if s not in outputs:
                    outputs.append(s)
                else:
                    outputs.remove(s)
                    inputs.remove(s)
                    s.close()
                    del request_message[s]
                    return False
            else:
                badReq = "HTTP/1.0 400 Bad Request"
                badReq = badReq.encode()
                connection.send(badReq)
                s.close()
                return False
    print("\033[1;32m[LOG]\033[1;0m: Connection timed out")
    s.close()
    return False

def main():
    if len(sys.argv) < 3:
        print("\033[1;31m[ERROR]\033[1;0m: Not enough arguments provided \nUsage: python3 sws.py ip_address port_number")
        exit(1)
    ip = sys.argv[1]
    port = sys.argv[2]

    if not validate_port(port) or not validate_ip(ip):
        exit(0)

    
    if (server := create_server(ip, port)) == None:
        exit(0)
    
    inputs = [server]
    outputs = []
    request_message = {}
    while True:
        readable, writeable, exception = select.select(inputs, outputs, inputs)
        for s in readable:
            if s is server:
                connection, address = s.accept()
                connection.setblocking(0)
                print("new connection")
                inputs.append(connection)
                request_message[connection] = queue.Queue()
                process_new_readable_connection(s, connection, address, inputs, outputs)      

main()
