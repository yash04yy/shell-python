import sys
import os
import subprocess
import shlex

def main():
    while(True):
        sys.stdout.write("$ ")
        command = input()
        if command == "exit":
            break
        elif command.startswith("echo "):
            args = shlex.split(command)
            # echo 'shell hello'
            #becomes:
            #['echo', 'shell hello']
            print(" ".join(args[1:]))
        elif command.startswith("type "):
            args = shlex.split(command)
            target = args[1]
            builtins = {"echo","exit","type","pwd"}
            if target in builtins:
                print(f"{target} is a shell builtin")
            else:
                path_env = os.getenv("PATH")
                path_dirs = path_env.split(':')
                found = False
                for path_dir in path_dirs:
                    file_path = path_dir + '/' + target
                    if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                        print(f"{target} is {file_path}")
                        found = True
                        break
                if not found:
                    print(f"{target}: not found")
        elif command == "pwd":
            cur_dir = os.getcwd()
            print(cur_dir)
        elif command.startswith("cd "):
            try:
                to_dir = command[3:]
                if to_dir.startswith("~"):
                    home = os.getenv("HOME")
                    to_dir = to_dir.replace("~",home)
                os.chdir(to_dir)
            except FileNotFoundError:
                print(f"cd: {to_dir}: No such file or directory")
                
        else:
            # Coverts $ python3 --version
            #to ['python3', '--version']
            args = shlex.split(command)
            target = args[0]
            path_env = os.getenv("PATH")
            path_dirs = path_env.split(':')
            found = False
            for path_dir in path_dirs:
                file_path = path_dir + '/' + target
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    subprocess.run(args,executable=file_path)
                    found = True
                    break
            if not found:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()
