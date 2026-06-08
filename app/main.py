import sys
import os
import subprocess
import shlex
import readline

# Global list of builtins required by the autocomplete stages
BUILTINS = ["echo", "exit", "type", "pwd", "cd"]

def get_all_matches(text):
    """
    Finds all builtins and PATH executables starting with `text`.
    """
    matches = set()
    # 1. Check builtins
    for b in BUILTINS:
        if b.startswith(text):
            matches.add(b)
    
    # 2. Check executables in PATH using directory loop style
    path_env = os.getenv("PATH")
    if path_env:
        path_dirs = path_env.split(':')
        for path_dir in path_dirs:
            if not os.path.isdir(path_dir):
                continue
            try:
                for filename in os.listdir(path_dir):
                    if filename.startswith(text):
                        file_path = path_dir + '/' + filename
                        if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                            matches.add(filename)
            except OSError:
                continue
                
    return sorted(list(matches))

def longest_common_prefix(strs):
    """Returns the longest common prefix among a list of strings."""
    if not strs:
        return ""
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix

def completer(text, state):
    """
    Custom completion engine that implements Longest Common Prefix (LCP),
    trailing spaces for unique matches, and custom behavior matching Bash.
    """
    if state == 0:
        # Fetch all matching commands globally
        completer.matches = get_all_matches(text)

        if not completer.matches:
            # Stage: Handling Invalid Completions (Ring Bell)
            sys.stdout.write('\x07')
            sys.stdout.flush()
            return None

        if len(completer.matches) > 1:
            # Stage: Completing to Longest Common Prefix (LCP)
            lcp = longest_common_prefix(completer.matches)

            # If the common prefix extends beyond what the user typed, complete up to it!
            if lcp and lcp != text:
                return lcp
            
            # FIXED: Do not manually ring bells or exit early with None here.
            # Returning the list items sequentially allows readline to handle the 
            # 1st tab (bell) and 2nd tab (print choices layout) automatically.
            sys.stdout.write("\x07")
            sys.stdout.flush()

    # Return candidates matching index states
    if state < len(completer.matches):
        match = completer.matches[state]
        # Append a trailing space only if it's a definitive single match
        if len(completer.matches) == 1:
            return match + " "
        return match
    else:
        return None

# Initialize completer matches cache attribute
completer.matches = []

# --- Configure Readline Engine Hooks ---
readline.set_completer(completer)
if "libedit" in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")
else:
    readline.parse_and_bind("tab: complete")
readline.set_completer_delims(" \t\n\"\\'`@$><=;|&|")
def main():
    while(True):
        # Readline automatically outputs the prompt and handles inline editing/TABS!
        try:
            command = input("$ ")
        except (EOFError, KeyboardInterrupt):
            break

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

        if "2>>" in args:
            idx = args.index("2>>")
            if idx + 1 < len(args):
                redirect_stderr = (args[idx+1],"a")
                args = args[:idx]
            else:
                print("shell: syntax error near unexpected token `newline'")
                continue

        #Look for Standard Error Redirection (2>)
        if "2>" in args:
            idx = args.index("2>")
            if idx + 1 < len(args):
                redirect_stderr = (args[idx+1],"w")
                args = args[:idx]
            else:
                print("shell: syntax error near unexpected token `newline'")
                continue
        
        if ">>" in args or "1>>" in args:
            # Find the index of the operator
            if ">>" in args:
                idx = args.index(">>")
            else:
                idx = args.index("1>>")

            # The file path is the argument immediately following the operator
            if idx + 1 < len(args):
                redirect_stdout = (args[idx+1],"a")
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
                redirect_stdout = (args[idx+1],"w")
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
                path,mode = redirect_stderr
                with open(path, mode) as f:
                    pass
            if redirect_stdout:
                path,mode = redirect_stdout
                with open(path, mode) as f:
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
                path,mode = redirect_stderr
                with open(path, mode) as f:
                    pass
            if redirect_stdout:
                path,mode = redirect_stdout
                with open(path, mode) as f:
                    f.write(output_msg + "\n")
            else:
                print(output_msg)
        elif cmd_name == "pwd":
            cur_dir = os.getcwd()
            if redirect_stderr:
                path,mode = redirect_stderr
                with open(path, mode) as f:
                    pass
            if redirect_stdout:
                path,mode = redirect_stdout
                with open(path, mode) as f:
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
                    path,mode = redirect_stderr
                    with open(path, mode) as f:
                        pass
            except FileNotFoundError:
                err_msg = f"cd: {to_dir}: No such file or directory"
                if redirect_stderr:
                    path,mode = redirect_stderr
                    with open(path, mode) as f:
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
                        out_path, out_mode = redirect_stdout
                        err_path, err_mode = redirect_stderr
                        with open(out_path, out_mode) as f_out, open(err_path, err_mode) as f_err:
                            subprocess.run(args, executable=file_path, stdout=f_out, stderr=f_err)
                    elif redirect_stdout:
                        out_path, out_mode = redirect_stdout
                        with open(out_path, out_mode) as f_out:
                            subprocess.run(args, executable=file_path, stdout=f_out)
                    elif redirect_stderr:
                        err_path, err_mode = redirect_stderr
                        with open(err_path, err_mode) as f_err:
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
