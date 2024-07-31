import time
import os
import threading
import sys
import console
import fileIO
import servers

def print_main_menu():
    menu_string = "main menu\n"
    menu_string += '%-*s    Status\n\n' % (20,"Server name")
    for server in servers.server_objects.values():
        if not server.is_running and not server.is_sleeping:
            menu_string += '%-*s    | %s\n' % (20,server.name,"off")
            continue
        if server.is_running:
            menu_string += '%-*s    | %s\n' % (20, server.name,"running")
            continue
        if server.is_sleeping:
            menu_string += '%-*s    | %s\n' % (20,server.name,"sleeping")
            continue
    print(menu_string, end= "")
        
def process_input(input: str):
    stripped_input = input.strip()
    (command, separator, args) = stripped_input.partition(' ')
    if console.selected_server is not None and not command == '?':
        servers.server_objects[console.selected_server]._receive_stdin(input)
        console.log(console.selected_server, input)
        return
    if command == '?':
        stripped_input = args.strip()
        (command, separator, args) = stripped_input.partition(' ')
    if command in console.commands.keys():
        console.commands[command]["func"](args)
        return

    print(f'Unknown command \'{command}\' use \'help\' for a list of commands.')

def _help(args):
    print()
    if (command := validate_server_name_arg(args, False)):
        if command not in console.commands.keys():
            print(f'Unknown command \'{command}\' use \'help\' for a list of commands.')
            return
        print('%-*s%s' % (10, f'{command}:', console.commands[command]["bio"]))
        if console.commands[command]["help"]: print('%-*s%s' % (10, "", console.commands[command]["help"]))
        return
    for command in console.commands.keys():
        print('%-*s%s' % (10, f'{command}:', console.commands[command]["bio"]))
        if console.commands[command]["help"]: print('%-*s%s' % (10, "", console.commands[command]["help"]))
        # print(f'{command}: \t{console.commands[command]["help"]}')
        print()

def _quit(args):
    print("Quitting program!")
    running_servers = [server for server in servers.server_objects.values() if server.is_running or server.is_sleeping]
    if running_servers:
        if input("Servers are still running, do you wish to stop them in order to quit? [y/n]\n").lower().strip() != 'y':
            print("Did not quit the program because of running server(s)!")
            return
        
        for server in running_servers:
            if not server.stop(): 
                print("Did not quit the program because of running server(s)!")
                return
    print("Quit succesfully :)")
    exit(0)

def _refresh(args):
    if console.selected_server is None:
        _hub(args)
        return
    console.clear_console()
    console.print_server_log(console.selected_server)

def _hub(args):
    console.selected_server = None
    console.clear_console()
    print_main_menu()

def _reload(args):
    servers.reload_servers()
    print("reload succesfull")

def _select(args):
    if not (server_name := validate_server_name_arg(args, True)):
        print("Invalid argument, see 'help'.")
        return
    console.clear_console()
    console.selected_server = server_name
    console.print_server_log(server_name)
    
def _stop(args):
    if not (server_name := validate_server_name_arg(args, True)):
        print("Invalid argument, see 'help'.")
        return
    servers.server_objects[server_name].stop()
    # threading.Thread(target=servers.server_objects[server_name].stop).start()
    
def _start(args):
    if not (server_name := validate_server_name_arg(args, True)):
        print("Invalid argument, see 'help'.")
        return
    if not servers.port_available(server_name): return
    servers.server_objects[server_name].start()
    
def _sleep(args):
    if not (server_name := validate_server_name_arg(args, True)):
        print("Invalid argument, see 'help'.")
        return
    if not servers.port_available(server_name): return
    servers.server_objects[server_name].sleep()                 

def validate_server_name_arg(args, check_server_existance) -> str:
    stipped_args = args.strip()
    if stipped_args == "":
        # print("No arguments given, provide server name!")
        return ""
    
    if stipped_args[0] == "\"":
        (server_name, separator, tail) = stipped_args[1:].partition("\"")
        if separator == "":
            # print("Invalid argument given!")
            return ""
        if tail == "":
            if servers.server_exists(server_name):
                return server_name
            return ""
        if tail[0] == " ":
            # print("Too many arguments given, provide only the server name!")
            return ""
        # print("Invalid argument given!")
        return ""            
    
    if stipped_args.find(" ") >= 0:
        # print("Too many arguments given, provide only the server name!")
        return ""
    if stipped_args.find("\"") >= 0:
        # print("Invalid argument given!")
        return ""
    if not check_server_existance: return stipped_args
    if servers.server_exists(stipped_args):
        return stipped_args
    return ""

if __name__ == '__main__':

    program_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(program_path)

    console.commands = {
        "quit":{
            "func": _quit,
            "bio": "Quits the program, if any servers are running it will give you the option to stop them.",
            "help": ""
        },
        "refresh":{
            "func": _refresh,
            "bio": "Refreshes the current screen with up-to-date data.",
            "help": ""
        },
        "select":{
            "func": _select,
            "bio": "Select a server to view and control.",
            "help": "Usage: select server_name"
        },
        "stop":{
            "func": _stop,
            "bio": "Stop the specified server.",
            "help": "Usage: stop server_name"
        },
        "start":{
            "func": _start,
            "bio": "Start the specified server.",
            "help": "Usage: start server_name"
        },
        "sleep":{
            "func": _sleep,
            "bio": "Sleep the specified server.",
            "help": "Usage: sleep server_name"
        },
        "hub":{
            "func": _hub,
            "bio": "Returns you to the main menu.",
            "help": ""
        },
        "reload":{
            "func": _reload,
            "bio": "Updates server configs and creates new server if any were added",
            "help": ""
        },
        "help":{
            "func": _help,
            "bio": "Print all commands or get help with a specified command",
            "help": "Usage: help [command]"
        }
    }
                                                                 
    servers.server_objects = servers.create_servers()
    
    servers.on_boot_servers()
    _hub("")

    while True:
        cli_input = sys.stdin.readline()
        process_input(cli_input)
