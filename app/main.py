import sys
import os

def main():
    while(True):
        sys.stdout.write("$ ")
        command = input()
        if command == "exit":
            break
        elif command.startswith("echo "):
            print(command[5:])
        elif command.startswith("type "):
            target = command[5:]
            builtins = {"echo","exit","type"}
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
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
