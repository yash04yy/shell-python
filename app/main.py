import sys
import os
import subprocess
import shlex

def main():
    while(True):
        sys.stdout.write("$ ")
        command = input()

        try:
            # echo 'shell hello'
            #becomes:
            #['echo', 'shell hello']
            args = shlex.split(command)
        except ValueError as e:
            print(f"shell: {e}")
            continue

        if not args:
            continue

        redirect_file = None

        # Look for '>' or '1>' in the arguments
        if ">" in args or "1>" in args:
            # Find the index of the operator
            if ">" in args:
                idx = args.index(">")
            else:
                idx = args.index("1>")

            # The file path is the argument immediately following the operator
            if idx + 1 < len(args):
                redirect_file = args[idx+1]
                args = args[:idx]
            else:
                print("shell: syntax error near unexpected token `newline'")
                continue

        if not args:
            continue
        cmd_name = args[0]

        if cmd_name == "exit":
            break
        elif cmd_name == "echo":
            output_str = " ".join(args[1:])
            if redirect_file:
                with open(redirect_file, "w") as f:
                    f.write(output_str + "\n")
            else:
                print(output_str)

        elif cmd_name == "type":
            if len(args) < 2:
                continue
            target = args[1]
            builtins = {"echo","exit","type","pwd"}
            if target in builtins:
                output_msg = f"{target} is a shell builtin"
            else:
                path_env = os.getenv("PATH")
                path_dirs = path_env.split(':')
                found = False
                for path_dir in path_dirs:
                    file_path = path_dir + '/' + target
                    if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                        output_msg = f"{target} is {file_path}"
                        found = True
                        break
                if not found:
                    output_msg = f"{target}: not found"
                if redirect_file:
                    with open(redirect_file, "w") as f:
                        f.write(output_msg + "\n")
                else:
                    print(output_msg)
        elif cmd_name == "pwd":
            cur_dir = os.getcwd()
            if redirect_file:
                with open(redirect_file, "w") as f:
                    f.write(cur_dir + "\n")
            else:
                print(cur_dir)
        elif cmd_name == "cd ":
            try:
                to_dir = args[1] if len(args) > 1 else "~"
                if to_dir.startswith("~"):
                    home = os.getenv("HOME")
                    to_dir = to_dir.replace("~",home)
                os.chdir(to_dir)
            except FileNotFoundError:
                print(f"cd: {to_dir}: No such file or directory")
                
        else:
            # Coverts $ python3 --version
            #to ['python3', '--version']
            target = args[0]
            path_env = os.getenv("PATH")
            path_dirs = path_env.split(':')
            found = False
            for path_dir in path_dirs:
                file_path = path_dir + '/' + target
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    if redirect_file:
                        with open(redirect_file, "w") as f:
                            subprocess.run(args,executable=file_path,stdout=f)
                    else:
                        subprocess.run(args,executable=file_path)
                    found = True
                    break
            if not found:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()
