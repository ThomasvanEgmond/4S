import json
import uuid
import struct
import console
import socketserver
import threading
import time

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass

class Minecraft:
    class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
        """
        The request handler class for our server.

        It is instantiated once per connection to the server, and must
        override the handle() method to implement communication to the
        client.
        """
        def handle(self):
            # self.request is the TCP socket connected to the client
            super()
            data = self.request.recv(1024)
            addr = self.client_address
            client_ip = addr[0]

            try:
                (length, i) = self.read_varint(data, 0)
                (packetID, i) = self.read_varint(data, i)

                if packetID == 0:
                    (version, i) = self.read_varint(data, i)
                    (ip, i) = self.read_utf(data, i)

                    ip = ip.replace('\x00', '').replace("\r", "\\r").replace("\t", "\\t").replace("\n", "\\n")
                    is_using_fml = False

                    if ip.endswith("FML"):
                        is_using_fml = True
                        ip = ip[:-3]

                    (port, i) = self.read_ushort(data, i)
                    (state, i) = self.read_varint(data, i)

                    if state == 1:
                        console.print_log(self.server.name, ("[%s:%s] Received client " + ("(using ForgeModLoader) " if is_using_fml else "") +
                                            "ping packet (%s:%s).\n") % (ip, port, client_ip, addr[1]))
                        returnPacket = {}
                        returnPacket["version"] = {}
                        returnPacket["version"]["name"] = self.server.config["version_text"]
                        returnPacket["version"]["protocol"] = self.server.config.get("protocol", 2)
                        returnPacket["players"] = {}
                        returnPacket["players"]["max"] = self.server.config.get("player_max", 0)
                        returnPacket["players"]["online"] = self.server.config.get("players_online", 0)
                        returnPacket["players"]["sample"] = []

                        for sample in self.server.config["samples"]:
                            returnPacket["players"]["sample"].append({"name": sample, "id": str(uuid.uuid4())})

                        returnPacket["description"] = {"text": self.server.config["motd"]["1"] + "\n" + self.server.config["motd"]["2"]}

                        if self.server.config["server_icon"] and len(self.server.config["server_icon"]) > 0:
                            returnPacket["favicon"] = self.server.config["server_icon"]

                        self.write_response(json.dumps(returnPacket))
                        if self.server.config["wake_on_status_packet"]: self.server.shutdown()
                    elif state == 2:
                        name = ""
                        if len(data) != i:
                            (some_int, i) = self.read_varint(data, i)
                            (some_int, i) = self.read_varint(data, i)
                            (name, i) = self.read_utf(data, i)
                        console.print_log(self.server.name, 
                            ("[%s:%s] " + (name + " t" if len(name) > 0 else "T") + "ries to connect to the server " +
                                ("(using ForgeModLoader)" if is_using_fml else "") + "(%s:%s).\n")
                            % (client_ip, addr[1], ip, port))
                        kick_message = ""
                        for message in self.server.config["kick_message"]:
                            kick_message += message + "\n"
                        self.write_response(json.dumps({"text": kick_message}))
                        if self.server.config["wake_on_join_packet"]: self.server.shutdown()
                    else:
                        console.print_log(self.server.name, "[%s:%d] Tried to request a login/ping with an unknown state: %d\n" % (client_ip, addr[1], state))
                        if self.server.config["wake_on_other_packets"]: self.server.shutdown()
                        
                elif packetID == 1:
                    (long, i) = self.read_long(data, i)
                    response = bytearray()
                    self.write_varint(response, 9)
                    self.write_varint(response, 1)
                    bytearray.append(long)
                    self.request.sendall(bytearray)
                    console.print_log(self.server.name, "[%s:%d] Responded with pong packet.\n" % (client_ip, addr[1]))
                else:
                    console.print_log(self.server.name, "[%s:%d] Sent an unexpected packet: %d\n" % (client_ip, addr[1], packetID))
                    if self.server.config["wake_on_other_packets"]: self.server.shutdown()   

            except (TypeError, IndexError):
                console.print_log(self.server.name, "[%s:%s] Received invalid data (%s)\n" % (client_ip, addr[1], data))
                if self.server.config["wake_on_other_packets"]: self.server.shutdown()

        def write_response(self, response):
            response_array = bytearray()
            self.write_varint(response_array, 0)
            self.write_utf(response_array, response)
            length = bytearray()
            self.write_varint(length, len(response_array))
            self.request.sendall(length)
            self.request.sendall(response_array)

        def read_varint(self, byte, i):
            result = 0
            bytes = 0
            while True:
                byte_in = byte[i]
                i += 1
                result |= (byte_in & 0x7F) << (bytes * 7)
                if bytes > 32:
                    raise IOError("Packet is too long!")
                if (byte_in & 0x80) != 0x80:
                    return result, i


        def read_utf(self, byte, i):
            (length, i) = self.read_varint(byte, i)
            ip = byte[i:(i + length)].decode('utf-8')
            i += length
            return ip, i


        def read_ushort(self, byte, i):
            new_i = i + 2
            return struct.unpack(">H", byte[i:new_i])[0], new_i


        def read_long(self, byte, i):
            new_i = i + 8
            return struct.unpack(">q", byte[i:new_i]), new_i


        def write_varint(self, byte, value):
            while True:
                part = value & 0x7F
                value >>= 7
                if value != 0:
                    part |= 0x80
                byte.append(part)
                if value == 0:
                    break


        def write_utf(self, byte, value):
            self.write_varint(byte, len(value))
            for b in value.encode():
                byte.append(b)

    class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):
        """
        The request handler class for our server.

        It is instantiated once per connection to the server, and must
        override the handle() method to implement communication to the
        client.
        """
        def handle(self):
            data = self.request[0].strip()
            socket = self.request[1]
            console.print_log(self.server.name, f'Received client ping packet ({self.client_address[0]}:{self.client_address[1]}).\n')
            server_data_string = "MCPE;Opstarten...;671;;0;10;9360904171923126593;Bedrock level;Survival;1;19132;19133;0;"
            request_status_response = bytearray(b'\x1c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx')
            request_status_response += len(server_data_string).to_bytes(2)
            request_status_response += server_data_string.encode()
            # request_status_response = b'\x1c\x00\x00\x00\x00\x00\x00\x00\x00\x81\xe8\x9c\xbf\x87\xf39A\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx\x00`MCPE;billen boobies;671;1.20.81;0;10;9360904171923126593;Bedrock level;Survival;1;19132;19133;0;'
            socket.sendto(request_status_response, self.client_address)
            socket.sendto(request_status_response, self.client_address)
            socket.sendto(request_status_response, self.client_address)
            self.server.shutdown()
        
    def __init__(self, name, is_bedrock: bool, config: dict) -> None:
        self.name = name
        self.is_bedrock = is_bedrock
        self.config = config
        self.server_thread = None

    def run(self,):
        HOST, PORT = self.config["ip"], self.config["port"]
        if self.is_bedrock: self.server = ThreadedUDPServer((HOST, PORT), self.ThreadedUDPRequestHandler)
        else: self.server = ThreadedTCPServer((HOST, PORT), self.ThreadedTCPRequestHandler)
        with self.server:
            ip, port = self.server.server_address

            # Start a thread with the server -- that thread will then start one
            # more thread for each request
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)

            self.server.name = self.name
            self.server.config = self.config
            self.server_thread.start()
            console.print_log(self.name, f'Now sleeping, send packets to wake!\n')
            self.server_thread.join()

    def start(self,):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        while self.server_thread is None or not self.server_thread.is_alive():
            time.sleep(0.01)

    def stop(self,) -> bool:
        self.server.shutdown()
        self.thread.join()
        return True

