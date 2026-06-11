import sys
import os
import subprocess
import shlex
import readline

# Global list of builtins required by the autocomplete stages
BUILTINS = ["echo", "exit", "type", "pwd", "cd","complete"]

# ==============================================================================
# AUTOCOMPLETE & TAB COMPLETION MODULE
# ==============================================================================
def handle_complete(args,stdout_redirect, stderr_redirect):
    if len(args) >=3 and args[1] == '-p':
        cmd = args[2]
        write_output(
            f"complete: {cmd}: no completion specification",
            stdout_redirect,
            stderr_redirect
        )

def get_command_matches(text):
    """Finds all builtins and PATH executables starting with `text`."""
    matches = set(b for b in BUILTINS if b.startswith(text))
    
    path_env = os.getenv("PATH")
    if path_env:
        for path_dir in path_env.split(':'):
            if not os.path.isdir(path_dir):
                continue
            try:
                for filename in os.listdir(path_dir):
                    if filename.startswith(text):
                        file_path = os.path.join(path_dir, filename)
                        if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                            matches.add(filename)
            except OSError:
                continue
    return sorted(list(matches))

def get_filename_matches(text):
    """Finds matching files/directories based on the prefix."""
    if '/' in text:
        dir_path, prefix = text.rsplit('/', 1)
        search_dir = dir_path if dir_path else '/'
    else:
        search_dir = '.'
        prefix = text

    if not os.path.isdir(search_dir):
        return []

    matches = []
    try:
        for entry in os.listdir(search_dir):
            if entry.startswith(prefix):
                if entry.startswith('.') and not prefix.startswith('.'):
                    continue
                matches.append(entry)
    except OSError:
        return []

    return sorted(matches)

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
    """Unified completion engine handling commands and paths."""
    if state == 0:
        line_buffer = readline.get_line_buffer()
        stripped_leading = line_buffer.lstrip()
        is_argument = ' ' in stripped_leading
        
        if not is_argument:
            completer.raw_matches = get_command_matches(text)
            completer.mode = "command"
        else:
            completer.mode = "filename"
            completer.raw_matches = get_filename_matches(text)

        if not completer.raw_matches:
            sys.stdout.write('\x07')
            sys.stdout.flush()
            return None

        if len(completer.raw_matches) > 1:
            lcp_raw = longest_common_prefix(completer.raw_matches)
            if completer.mode == "filename" and '/' in text:
                dir_part, _ = text.rsplit('/', 1)
                lcp_full = dir_part + '/' + lcp_raw
            else:
                lcp_full = lcp_raw

            if lcp_full and lcp_full != text:
                completer.display_matches = [lcp_full]
                return lcp_full
            
            sys.stdout.write("\x07")
            sys.stdout.flush()

            completer.display_matches = []
            for match in completer.raw_matches:
                if completer.mode == "filename" and '/' in text:
                    dir_part, _ = text.rsplit('/', 1)
                    full_path = os.path.join(dir_part, match)
                    display_name = dir_part + '/' + match
                else:
                    full_path = match
                    display_name = match

                if completer.mode == "filename" and os.path.isdir(full_path):
                    completer.display_matches.append(display_name + "/")
                else:
                    completer.display_matches.append(display_name)
        else:
            single_match = completer.raw_matches[0]
            if completer.mode == "command":
                completer.display_matches = [single_match + " "]
            else:
                if '/' in text:
                    dir_part, _ = text.rsplit('/', 1)
                    full_path = os.path.join(dir_part, single_match)
                    completed_path = dir_part + '/' + single_match
                else:
                    full_path = single_match
                    completed_path = single_match

                if os.path.isdir(full_path):
                    completer.display_matches = [completed_path + "/"]
                else:
                    completer.display_matches = [completed_path + " "]

    if state < len(completer.display_matches):
        return completer.display_matches[state]
    return None

# Initialize memory cache attributes
completer.raw_matches = []
completer.display_matches = []
completer.mode = "command"

# ==============================================================================
# PARSING & STREAM I/O MODULE
# ==============================================================================

def parse_redirections(args):
    """
    Extracts redirection operators and their targets from arguments.
    Returns (cleaned_args, stdout_redirect, stderr_redirect)
    """
    redirect_stdout = None
    redirect_stderr = None
    
    # Operators to look for, order of checking matters for precedence
    operators = ["2>>", "2>", ">>", "1>>", ">", "1>"]
    
    for op in operators:
        while op in args:
            idx = args.index(op)
            if idx + 1 >= len(args):
                print("shell: syntax error near unexpected token `newline`")
                return None, None, None
            
            target_file = args[idx+1]
            mode = "a" if ">>" in op else "w"
            
            if op.startswith("2"):
                redirect_stderr = (target_file, mode)
            else:
                redirect_stdout = (target_file, mode)
                
            # Strip out the operator and its target parameter
            args = args[:idx] + args[idx+2:]
            
    return args, redirect_stdout, redirect_stderr

def write_output(message, stdout_redirect, stderr_redirect, error_msg=None):
    """Helper to handle standardized writing to stdout/stderr or files."""
    # Process potential standard error output
    if stderr_redirect:
        path, mode = stderr_redirect
        with open(path, mode) as f:
            if error_msg:
                f.write(error_msg + "\n")
    elif error_msg:
        print(error_msg, file=sys.stderr)

    # Process standard out output
    if message is not None:
        if stdout_redirect:
            path, mode = stdout_redirect
            with open(path, mode) as f:
                f.write(message + "\n")
        else:
            print(message)

# ==============================================================================
# SHELL COMMAND EXECUTORS (BUILTINS & EXTERNALS)
# ==============================================================================

def handle_echo(args, stdout_redirect, stderr_redirect):
    output_str = " ".join(args[1:])
    write_output(output_str, stdout_redirect, stderr_redirect)

def handle_type(args, stdout_redirect, stderr_redirect):
    if len(args) < 2:
        return
    target = args[1]
    builtins_set = set(BUILTINS)
    
    if target in builtins_set:
        output_msg = f"{target} is a shell builtin"
    else:
        file_path = find_executable(target)
        if file_path:
            output_msg = f"{target} is {file_path}"
        else:
            output_msg = f"{target}: not found"
            
    write_output(output_msg, stdout_redirect, stderr_redirect)

def handle_pwd(args, stdout_redirect, stderr_redirect):
    cur_dir = os.getcwd()
    write_output(cur_dir, stdout_redirect, stderr_redirect)

def handle_cd(args, stdout_redirect, stderr_redirect):
    to_dir = args[1] if len(args) > 1 else "~"
    if to_dir.startswith("~"):
        home = os.getenv("HOME", "")
        to_dir = to_dir.replace("~", home)
    try:
        os.chdir(to_dir)
        write_output(None, stdout_redirect, stderr_redirect) # Trigger silent error-handling check
    except FileNotFoundError:
        err_msg = f"cd: {to_dir}: No such file or directory"
        write_output(None, stdout_redirect, stderr_redirect, error_msg=err_msg)

def find_executable(cmd_name):
    """Looks through PATH to find an executable binary."""
    path_env = os.getenv("PATH")
    if not path_env:
        return None
    for path_dir in path_env.split(':'):
        file_path = os.path.join(path_dir, cmd_name)
        if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
            return file_path
    return None

def execute_external(args, stdout_redirect, stderr_redirect):
    """Executes a system compiled application safely handling redirections."""
    cmd_name = args[0]
    exec_path = find_executable(cmd_name)
    
    if not exec_path:
        err_msg = f"{cmd_name}: command not found"
        write_output(None, stdout_redirect, stderr_redirect, error_msg=err_msg)
        return

    # Prepare file descriptors if redirections are requested
    f_out = open(stdout_redirect[0], stdout_redirect[1]) if stdout_redirect else None
    f_err = open(stderr_redirect[0], stderr_redirect[1]) if stderr_redirect else None

    try:
        subprocess.run(args, executable=exec_path, stdout=f_out or sys.stdout, stderr=f_err or sys.stderr)
    finally:
        if f_out: f_out.close()
        if f_err: f_err.close()

# ==============================================================================
# ENVIRONMENT SETUP & INTERPRETER LOOP
# ==============================================================================

# Setup Readline configurations globally
readline.set_completer(completer)
if "libedit" in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")
else:
    readline.parse_and_bind("tab: complete")
readline.set_completer_delims(" \t\n\"\\'`@$><=;|&|")


def main():
    while True:
        try:
            command = input("$ ")
        except (EOFError, KeyboardInterrupt):
            print() # Print clean line skip on exit
            break

        try:
            args = shlex.split(command)
        except ValueError as e:
            print(f"shell: {e}")
            continue

        if not args:
            continue

        # Process standard input tokens for streams
        parsed = parse_redirections(args)
        if parsed[0] is None: # Syntax Error encountered
            continue
        args, stdout_redirect, stderr_redirect = parsed

        if not args:
            continue
            
        cmd_name = args[0]

        # Route to respective modular functions
        if cmd_name == "exit":
            break
        elif cmd_name == "echo":
            handle_echo(args, stdout_redirect, stderr_redirect)
        elif cmd_name == "type":
            handle_type(args, stdout_redirect, stderr_redirect)
        elif cmd_name == "pwd":
            handle_pwd(args, stdout_redirect, stderr_redirect)
        elif cmd_name == "cd":
            handle_cd(args, stdout_redirect, stderr_redirect)
        elif cmd_name == "complete":
            handle_complete(args, stdout_redirect, stderr_redirect)
        else:
            execute_external(args, stdout_redirect, stderr_redirect)

if __name__ == "__main__":
    main()