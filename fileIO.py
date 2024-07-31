import os
import json

config_file = "4S_config.json"

def load_servers_config(servers_folder_name, program_path):

    servers_path = os.path.join(program_path, servers_folder_name)
    verify_servers_folder_existance(servers_folder_name, program_path)
    server_folders = [f.name for f in os.scandir(servers_folder_name) if f.is_dir()] # or f.name for name only or f.path
    servers_verify_config(server_folders, servers_path)

    return servers_get_config(server_folders, servers_path)

def verify_servers_folder_existance(servers_folder_name, servers_path):
    try:
        if not os.path.exists(servers_folder_name): os.mkdir(servers_path)
    except FileExistsError:
        print("This should never happen...")
        # print("Server with this name already exists!")
    except OSError:
        # print("Your server name caused an error, remove any of the following character \\ / : * ? \" < > or try shortening your server name!")
        print("Your servers folder name caused an error, remove any of the following character \\ / : * ? \" < > or try shortening your servers folder name!")

def get_default_config_file():
    configuration = {
        "on_boot": "off",
        "is_bedrock": False,
        "minecraft_server": {
            "ip": "",
            "port": 25565,
            "executable": "start.bat",
            "termination_delay": 30
        },
        "sleeper": {
            "sleep_after_stop": True,
            "ip": "",
            "kick_message": ["", "Komt er aan", ""],
            "motd": {"1": "Maintenance!", "2": "Check example.com for more information!"},
            "player_max": 0,
            "players_online": 0,
            "port": 25565,
            "protocol": 2,
            "samples": ["example.com", "", "Maintenance"],
            "server_icon": "server_icon.png",
            "show_ip_if_hostname_available": True,
            "wake_on_status_packet": False,
            "wake_on_join_packet": True,
            "wake_on_other_packets": False,
            "version_text": "Maintenance",
        },
        "close_empty_server": {
            "enabled": True,
            "timer": 300
        },
        "timed_commands": {
            "drinkieDoen":{
                "enabled": False,
                "command": "say drinkie doen",
                "timer": 2700
            }
        }
    }
    return configuration

def servers_verify_config(server_folders, servers_path):
    # add real json verification later
    for server_name in server_folders:
        config_path = os.path.join(servers_path, server_name, config_file)
        if not os.path.exists(config_path):
            configuration = get_default_config_file()
            with open(config_path, 'w') as file:
                json.dump(configuration, file, indent=4, ensure_ascii=False)

def servers_get_config(server_folders, servers_path):
    servers_config: dict[str, dict] = {}
    for server_name in server_folders:
        config_path = os.path.join(servers_path, server_name, config_file)
        with open(config_path, 'r') as file:
            config = json.load(file)
            servers_config[server_name] = config
    return servers_config

def get_server_config(server_path) -> dict:
    config_path = os.path.join(server_path, config_file)
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config