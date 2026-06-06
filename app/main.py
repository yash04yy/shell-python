import sys

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
                print(f"{command[5:]} is a shell builtin")
            else:
                print(f"type {command}: command not found")
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
