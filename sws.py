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
        #print("\033[1;31m[ERROR]\033[1;0m: Invalid IP Address: IP address must be a 4 octect IPV4 address")
        return False
    for octet in octets:
        try: 
            x = int(octet)
            if  x < 0 or x > 255:
                #print("\033[1;31m[ERROR]\033[1;0m: Invalid IP Address: Octets must be between 0 and 255")
                return False
        except:
            #print("\033[1;31m[ERROR]\033[1;0m: Invalid IP Address: Octects must only contain integers")
            return False  
    #print("\033[1;32m[LOG]\033[1;0m: IP Address Successfully Validated")
    return True


#Take a port number as an input and validates whether it is a valid port number
#
#@param port: The port to be validated
#@returns: true if it is a valid port number
def validate_port(port: str) -> bool:
    try:
        x = int(port)
    except: 
       # print("\033[1;31m[ERROR]\033[1;0m: Port number must be an integer")
        return False
    if(x < 0 or x > 65535):
       # print("\033[1;31m[ERROR]\033[1;0m: Port number must be between 0 and 65535")
        return False
   # print("\033[1;32m[LOG]\033[1;0m: Port Successfully Validated")
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
    #print("\033[1;32m[LOG]\033[1;0m: Server bound successfully at {}:{}, Beginning listener".format(ip, port))
    server.listen(5)
    return server


#Logs to the console all request that happem
def log(response, request, connection, address):
    t = time.localtime()
    day = ""
    month = ""
    match t.tm_wday:
        case 0:
            day = "Mon"
        case 1:
            day = "Tue"
        case 2:
            day = "Wed"
        case 3:
            day = "Thu"
        case 4: 
            day = "Fri"
        case 5:
            day = "Sat"
        case 6:
            day = "Sun"
    match t.tm_mon:
        case 0:
            month = "Jan"
        case 1:
            month = "Feb"
        case 2:
            month = "Mar"
        case 3: 
            month = "Apr"
        case 4:
            month = "May"
        case 5:
            month = "Jun"
        case 6:
            month = "Jul"
        case 7:
            month = "Aug"
        case 8:
            month = "Sep"
        case 9:
            month = "Oct"
        case 10: 
            month = "Nov"
        case 11:
            month = "Dec"
    request = request.replace("\r\n", "")
    request = request.strip()
    print("{} {} {} {}:{}:{} {} {}: {}:{} {};{}".format(day, month, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, time.tzname[0], t.tm_year, address[0], address[1], request, response))


# Sends the specified file through the connection
#
#@param: File: The path of the file to be sent
#@param: Connection: The connection to send the file over
#@exept: Throws an exception if the file is not accessible
def send_file(filename, connection):
    if filename[0] == "/":
        filename = filename[1:]
    f = open(filename, 'rb')
    req = "HTTP/1.0 200 OK\r\n\r\n"
    req = req.encode()
    connection.send(req)
    data = f.read(1024)
    while data:
        connection.send(data)
        data = f.read(1024)
    f.close()


# Takes a string in and parses the HTTP request in the string
#
# @param The http request to parse
# @returns: A touple containing a string representing the file to be found or and a boolean of if it is a persistent connection
# @except: Throws an exception if the request is invalid
def parse_http_request(request) -> (str, bool):
    filename = ""
    connection = False
    if request[0:4] == "GET " and " HTTP/1.0" in request:
        HTTPindex = request.find(" HTTP/1.0")
        filename = request[4:HTTPindex]
        conn = request[HTTPindex+9:]
        conn = conn.lower()
        conn = conn.strip()
        if len(conn) > 0 and conn.startswith("connection"):
            colon = conn.find(":")
            if conn[colon:] == ":keep-alive" or conn[colon:] == ": keep-alive":
                connection = True
            elif conn[colon:] == ":close" or conn[colon:] == ": close":
                pass
            else: 
                raise Exception("Invalid HTTP request")
        elif len(conn) == 0:
            pass 
        else:
            raise Exception("Invalid HTTP request")
        return (filename, connection)
    else:
        raise Exception("Invalid http request")


# Takes a new connection and processes it, closing when the connection is closed
#
#@param: Server: The server to process the request from
def process_new_readable_connection(s, connection, address, inputs, outputs):
    id = os.fork()
    message = ""
    messageQue = []
    if id != 0:
        return False
    second = time.time()
    while time.time() < second + 30:
        msg = None
        try:
            msg = connection.recv(1024).decode()
        except:
            pass
        if msg != None:
            second = time.time()

            message += msg
            messageQue = message.split("\r\n\r\n")
            for x in range(len(messageQue)):
                messageQue[x] = messageQue[x].strip()
                
            while len(messageQue) >0:
                try:
                    currMsg = messageQue.pop(0)
                    req = parse_http_request(currMsg)
                    if req[1] == True:
                        try:
                            send_file(req[0], connection)
                            log("HTTP/1.0 200 OK", currMsg, connection, address)
                        except:
                            badReq = "HTTP/1.0 404 Not Found\r\n\r\n"
                            log("HTTP/1.0 404 Not Found", currMsg, connection, address)
                            badReq = badReq.encode()
                            connection.send(badReq)
                    else:
                        try:
                            send_file(req[0], connection)
                            log("HTTP/1.0 200 OK", currMsg, connection, address)
                        except:
                            badReq = "HTTP/1.0 404 Not Found\r\n\r\n"
                            log("HTTP/1.0 404 Not Found", currMsg, connection, address)
                            badReq = badReq.encode()
                            connection.send(badReq)
                        connection.close()
                        exit(0)
                except:
                    badReq = "HTTP/1.0 400 Bad Request\r\n\r\n"
                    log("HTTP/1.0 400 Bad Request", currMsg, connection, address)
                    badReq = badReq.encode()
                    connection.send(badReq)
                    connection.close()
                    exit(0)
    #print("\033[1;32m[LOG]\033[1;0m: Connection timed out")
    s.close()
    exit(0)

def main():
    if len(sys.argv) < 3:
        #print("\033[1;31m[ERROR]\033[1;0m: Not enough arguments provided \nUsage: python3 sws.py ip_address port_number")
        exit(1)
    ip = sys.argv[1]
    port = sys.argv[2]

    if not validate_port(port) or not validate_ip(ip):
        exit(0)

    
    if (server := create_server(ip, port)) == None:
        exit(0)
    

    while True:
        inputs = [server]
        outputs = []
        readable, writeable, exception = select.select(inputs, outputs, inputs)
        for s in readable:
            if s is server:
                connection, address = s.accept()
                connection.setblocking(0)
                inputs.append(connection)
                try:
                    process_new_readable_connection(s, connection, address, inputs, outputs)      
                except:
                    exit(0)

main()
