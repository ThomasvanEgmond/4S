import os
import time
import psutil
import struct
import threading
import subprocess
import mcstatus
import console
from wakepy import keep

class Server:
    def __init__(self, name, config, servers_folder_path):
        self.name = name
        self.config = config
        self.server_path = os.path.join(servers_folder_path, self.name)
        self.ip = config["minecraft_server"]["ip"]
        self.port = config["minecraft_server"]["port"]
        self.is_bedrock = config["is_bedrock"]
        self.close_empty_server_timer = config["close_empty_server"]["timer"]
        self.utilization_update_delay = 1
        self.status_update_delay = 0.1
        self.mcserver_process = None
        self.memory_usage = 0
        self.os_mcserver_process = None
        self.mcstatus_status = None
        
    def start(self,):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
         # if self.is_bedrock: self.update_bedrock_server()
        server_executable_path = os.path.join(self.server_path, self.config["minecraft_server"]["executable"])
        try:
            self.mcserver_process = subprocess.Popen(server_executable_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True, cwd=self.server_path)
        except FileNotFoundError as e:
            print(f'{server_executable_path} not found!')
            return False
        while self.mcserver_process is None:
            time.sleep(0.01)
        return True

    def stop(self,):
        self.send_command("stop")

    def terminate(self,) -> bool:
        self.os_mcserver_process.terminate()
        self.mcserver_process.terminate()
        while self.mcserver_process.poll() is None:
            time.sleep(0.1)
        return True

    def send_command(self, command):
        if self.mcserver_process.poll() is None:
            self.mcserver_process.stdin.write(f'{command}\n')
            try:
                self.mcserver_process.stdin.flush()
            except OSError:
                pass
    
    def update_bedrock_server(self,):
        bedrock_updater_path = os.path.join(self.server_path, "MinecraftBedrockServerUpdateScript.ps1")
        subprocess.run(["powershell.exe", bedrock_updater_path], cwd = self.server_path, stdout=subprocess.PIPE) # make this OS indepented one day

    def record_process_utilization(self,):
        last_update = 0
        while self.mcserver_process.poll() is None:
            time.sleep(0.1)
            if (time.time() - last_update) < self.utilization_update_delay: continue
            try:
                last_update = time.time()
                self.memory_usage = int(self.os_mcserver_process.memory_info().rss / 1000 ** 2)
                os.system(f"title {self.name} - {self.memory_usage}MB")
            except psutil.NoSuchProcess as e:
                pass

    def get_real_server_process(self, server_subprocess_pid) -> psutil.Process: # if a batch file is used to start a server the server_subprocess.pid won't be that of the real server
        os_server_process = None
        if self.is_bedrock:
            return psutil.Process(server_subprocess_pid)
        while os_server_process is None:
            for child in psutil.Process(server_subprocess_pid).children(recursive=True):
                if child.memory_info().rss > 100 * 1000000: # select java process that has above 100MB RAM in use
                    return child

    def server_status_updater(self, ip, port):
        if not ip:
            ip = "localhost"
        if self.is_bedrock: mcstatus_server = mcstatus.BedrockServer.lookup(f"{ip}:{port}", 0.5)
        else: mcstatus_server = mcstatus.JavaServer.lookup(f'{ip}:{port}', 0.5)
        
        last_update = 0
        while self.mcserver_process.poll() is None:
            time.sleep(0.1)
            if (time.time() - last_update) < self.status_update_delay: continue
            try:
                self.mcstatus_status = mcstatus_server.status()
                last_update = time.time()
            except (TimeoutError, OSError, struct.error):
                pass

    def close_empty_server(self, timer):
        last_update = 0
        time_empty = 0
        time_last_filled = time.time()
        prev_time_empty = -1

        while self.mcserver_process.poll() is None:
            time.sleep(0.1)
            if self.mcstatus_status is None: continue
            if (time.time() - last_update) < self.status_update_delay: continue

            last_update = time.time()
            if self.mcstatus_status.players.online:
                time_last_filled = time.time()
                continue

            time_empty = int(time.time() - time_last_filled)
            if time_empty == prev_time_empty: continue
            prev_time_empty = time_empty

            if time_empty >= timer:
                self.stop()
                console.print_log(self.name, "Closing empty server!\n")
                return
            if time_empty == 0 and not (timer - time_empty) % 60 == 0:
                console.print_log(self.name, f'Server is empty, shutting down in {int(timer / 60)} minute(s) and {int(timer % 60)} second(s) if no one joins.\n')
            if (timer - time_empty) % 60 == 0:
                console.print_log(self.name, f'Server is empty, shutting down in {int((timer - time_empty) / 60)} minute(s) if no one joins.\n')

    def run_timed_commands(self, commands):
        server_start_time = int(time.time())
        last_update = server_start_time
        while self.mcserver_process.poll() is None:
            time.sleep(0.8)
            
            cur_time = int(time.time())
            if last_update == cur_time: continue
            last_update = cur_time

            for command in commands:
                if not command["enabled"]: continue
                if  (cur_time - server_start_time) % command["timer"] == 0:
                    console.print_log(self.name, f'Timed command: {command["command"]}\n')
                    self.send_command(command["command"])
            
    def log_stdout(self,):
        for line in self.mcserver_process.stdout:
            console.print_log(self.name, line, False)
    
    def run(self,):
        with keep.running() as k: # powercfg /request so the pc doesn't shutdown while the server is running, make this OS indepented one day
            
            while self.mcserver_process is None:
                time.sleep(0.01)

            self.os_mcserver_process = self.get_real_server_process(self.mcserver_process.pid)

            threading.Thread(target=self.log_stdout, daemon=True).start()
            threading.Thread(target=self.record_process_utilization, daemon=True).start()
            self.status_update_tread = threading.Thread(target=self.server_status_updater, args=[self.ip, self.port] ,daemon=True)
            self.status_update_tread.start()
            
            while self.mcstatus_status is None and self.mcserver_process.poll() is None:
                time.sleep(0.1)

            if enabled_timed_commands := [command for command in self.config["timed_commands"].values() if command["enabled"]]:
                threading.Thread(target=self.run_timed_commands, args=[enabled_timed_commands], daemon=True).start()

            if self.config["close_empty_server"]["enabled"]:
                threading.Thread(target=self.close_empty_server, args=[self.close_empty_server_timer], daemon=True).start()

            self.status_update_tread.join()
            self.mcserver_process.wait()
