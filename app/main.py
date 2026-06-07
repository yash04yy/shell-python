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

        redirect_stdout = None
        redirect_stderr = None

        #Look for Standard Error Redirection (2>)
        if "2>" in args:
            idx = args.index("2>")
            if idx + 1 < len(args):
                redirect_stderr = args[idx+1]
                args = args[:idx]
            else:
                print("shell: syntax error near unexpected token `newline'")
                continue

        # Look for '>' or '1>' in the arguments
        if ">" in args or "1>" in args:
            # Find the index of the operator
            if ">" in args:
                idx = args.index(">")
            else:
                idx = args.index("1>")

            # The file path is the argument immediately following the operator
            if idx + 1 < len(args):
                redirect_stdout = args[idx+1]
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
            if redirect_stderr:
                with open(redirect_stderr, "w") as f:
                    pass
            if redirect_stdout:
                with open(redirect_stdout, "w") as f:
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
            if redirect_stderr:
                with open(redirect_stderr, "w") as f:
                    pass
            if redirect_stdout:
                with open(redirect_stdout, "w") as f:
                    f.write(output_msg + "\n")
            else:
                print(output_msg)
        elif cmd_name == "pwd":
            cur_dir = os.getcwd()
            if redirect_stderr:
                with open(redirect_stderr, "w") as f:
                    pass
            if redirect_stdout:
                with open(redirect_stdout, "w") as f:
                    f.write(cur_dir + "\n")
            else:
                print(cur_dir)
        elif cmd_name == "cd":
            try:
                to_dir = args[1] if len(args) > 1 else "~"
                if to_dir.startswith("~"):
                    home = os.getenv("HOME")
                    to_dir = to_dir.replace("~",home)
                os.chdir(to_dir)
                if redirect_stderr:
                    with open(redirect_stderr, "w") as f:
                        pass
            except FileNotFoundError:
                err_msg = f"cd: {to_dir}: No such file or directory"
                if redirect_stderr:
                    with open(redirect_stderr,"w") as f:
                        f.write(err_msg + "\n")
                else: 
                    print(err_msg)
                
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
                    if redirect_stdout and redirect_stderr:
                        with open(redirect_stdout, "w") as f_out, open(redirect_stderr, "w") as f_err:
                            subprocess.run(args, executable=file_path, stdout=f_out, stderr=f_err)
                    elif redirect_stdout:
                        with open(redirect_stdout, "w") as f_out:
                            subprocess.run(args, executable=file_path, stdout=f_out)
                    elif redirect_stderr:
                        with open(redirect_stderr, "w") as f_err:
                            subprocess.run(args, executable=file_path, stderr=f_err)
                    else:
                        subprocess.run(args, executable=file_path)
                    found = True
                    break
            if not found:
                cmd_err = f"{target}: command not found"
                if redirect_stderr:
                    with open(redirect_stderr, "w") as f:
                        f.write(cmd_err + "\n")
                else:
                    print(cmd_err)


if __name__ == "__main__":
    main()
