import os
import threading
import sleeper
import time
import fileIO
import console
import minecraft as mc

class Server:
    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.config = config
        self.sleeper: sleeper.Minecraft = None
        self.mcserver: mc.Server = None
        self.capture_stdout_thread: threading.Thread = None
        self.termination_delay = self.config["minecraft_server"]["termination_delay"]
        self.print_to_stdout = False
        self.manual_sleep = False
        self.stdout_history = ""
        self.is_sleeping: bool = False
        self.is_running: bool = False
        self.thread: threading.Thread = None
        self.hold_thread = False
        self._reload_config()

    def run(self,):
        self._reload_config()
        if self.is_sleeping:
            self.sleeper.thread.join()
            while self.hold_thread:
                time.sleep(0.001)
            if self.is_sleeping:
                self.is_sleeping = False
                self.start()
    
        if self.is_running:
            self.mcserver.thread.join()
            while self.hold_thread:
                time.sleep(0.001)
            if not self.is_running: return
            self.is_running = False
            self._reload_config()
            if self.config["sleeper"]["sleep_after_stop"]:
                self.sleep()
                print("run")
                self.run()

    def start(self,) -> bool:
        self._reload_config()
        if self.is_running:
            console.print_log(self.name, f'{self.name} is already running.\n')
            return False
        
        self.hold_thread = True
        if self.is_sleeping:
            self.sleeper.stop()
            self.is_sleeping = False

        self.mcserver = mc.Server(self.name, self.config, servers_folder_path)
        if not self.mcserver.start():
            self.stop()
            self.hold_thread = False
            return False
        self.is_running = True

        self._start_thread()

        self.hold_thread = False
        console.print_log(self.name, f'Started {self.name}!\n')
        return True

    def sleep(self,) -> bool:
        self._reload_config()
        if self.is_sleeping:
            console.print_log(self.name, f'{self.name} is already sleeping.\n')
            return False
        
        self.hold_thread = True
        if self.is_running:
            self.stop()
            self.is_running = False

        self.sleeper = sleeper.Minecraft(self.name, self.config["is_bedrock"], self.config["sleeper"])
        self.sleeper.start()
        self.is_sleeping = True

        self._start_thread()

        self.hold_thread = False
        console.print_log(self.name, f'Sleeped {self.name}!\n')
        return True
        
    def stop(self,) -> bool:
        if not self.is_running and not self.is_sleeping:
            console.print_log(self.name, f'{self.name} is already stopped.\n')
            return False
        
        self.hold_thread = True
        if self.is_sleeping:
            self.sleeper.stop()
            self.is_sleeping = False
        if self.is_running:
            self.mcserver.stop()
            if not self._wait_for_stop():
                self.hold_thread = False
                return False
            self.is_running = False         

        self.hold_thread = False
        console.print_log(self.name, f'Stopped {self.name}!\n')
        return True
    
    def _receive_stdin(self, input):
        if not self.is_running: return
        self.mcserver.mcserver_process.stdin.write(input)
        if self.mcserver.mcserver_process.poll() is not None: return
        self.mcserver.mcserver_process.stdin.flush()

    def _reload_config(self,):
        server_path = os.path.join(servers_folder_path, self.name)
        self.config = fileIO.get_server_config(server_path)

    def _start_thread(self,):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run)
            self.thread.start()

    def _wait_for_stop(self,):
        stop_time = time.time()
        while self.mcserver.thread.is_alive():
            time.sleep(0.1)
            if not self.termination_delay: continue
            if time.time() - stop_time >= self.termination_delay:
                if input(f'{self.name} won\'t close, do you wish to terminate it? [y/n]\n').lower().strip() != 'y': return False
                self.mcserver.terminate()
                self.mcserver.thread.join()
                console.print_log(self.name, f'Terminated {self.name}\n')
                return True
        return True

def reload_servers():
    servers_config = fileIO.load_servers_config(servers_folder_name, program_path)
    existing_servers = server_objects.keys()
    removed_servers = [server for server in server_objects.keys() if server not in servers_config.keys()]
    for server in removed_servers:
        print(f'\'{server}\' was removed, deleting server object!')
        server_objects.pop(server)
    for server_name, config in servers_config.items():
        if server_name in existing_servers:
            server_objects[server_name].config = config
            continue
        print(f'Added \'{server_name}\'!')
        server_objects[server_name] = Server(server_name, config)
    return True

def create_servers() -> dict[str, Server]:
    servers_config = fileIO.load_servers_config(servers_folder_name, program_path)
    server_objects: dict[str, Server] = {}
    for server_name, config in servers_config.items():
        server_objects[server_name] = Server(server_name, config)
    return server_objects

def on_boot_servers():
    for server in server_objects.values():
        if not port_available(server.name): continue
        match server.config["on_boot"]:
            case "sleep":
                server.sleep()
            case "start":
                server.start()

def port_available(server_name):
    for server_object in server_objects.values():
        if server_object.name == server_name: continue
        share_server_port: bool = server_objects[server_name].config["sleeper"]["port"] == server_object.config["sleeper"]["port"] or server_objects[server_name].config["minecraft_server"]["port"] == server_object.config["minecraft_server"]["port"]
        if (server_object.is_running or server_object.is_sleeping) and share_server_port:
            print(f'{server_object.name} is already running on this port!')
            return False
    return True

def server_exists(server_name: str):
    if server_name not in server_objects.keys():
        print(f'{server_name} not found!')
        return False
    return True

servers_folder_name = "Servers"
program_path = os.path.dirname(os.path.realpath(__file__))
servers_folder_path = os.path.join(program_path, servers_folder_name)
server_objects: dict[str, Server] = None