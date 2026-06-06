import sys

def main():
    while(True):
        sys.stdout.write("$ ")
        command = input()
        if command == "exit":
            break
        if command.startswith("echo"):
            print(command.strip("echo"))
            break
        print(f"{command}: command not found")


if __name__ == "__main__":
    main()
