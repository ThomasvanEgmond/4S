import os
import servers
from datetime import datetime

selected_server: str | None = None
log_file = "4S_log.txt"
commands = {}
opened_logs = set()

def get_log_file(server_name, mode: str):
    server_path = os.path.join(servers.servers_folder_path, server_name)
    log_path = os.path.join(server_path, log_file)
    if server_name not in opened_logs:
        opened_logs.add(server_name)
        return open(log_path, 'w+')
    return open(log_path, mode)
    
def print_log(server_name, message, add_log_stamp = True):
    if add_log_stamp: 
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")
        log_stamp = f'[{time_stamp[:-3]} 4S] '
        message = log_stamp + message
    if selected_server is not None and server_name == selected_server:
        print(message, end="")
    with get_log_file(server_name, 'a+') as log_file:    
        log_file.write(message)
        log_file.flush()

def log(server_name, message):
    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")
    log_stamp = f'[{time_stamp[:-3]} 4S] '
    message = log_stamp + message
    with get_log_file(server_name, 'a+') as log_file:    
        log_file.write(message)
        log_file.flush()

def print_server_log(server_name):
    with get_log_file(server_name, 'r+') as log_file:    
        print(log_file.read(), end="")

def clear_console():
        if os.name == 'nt': #windows
            os.system('cls')
        else:
            os.system('clear')