import sys
import os
import subprocess
import shlex
import readline

# Global list of builtins required by the autocomplete stages
BUILTINS = ["echo", "exit", "type", "pwd", "cd"]

def get_command_matches(text):
    """Finds all builtins and PATH executables starting with `text`."""
    matches = set()
    for b in BUILTINS:
        if b.startswith(text):
            matches.add(b)
    
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

def get_filename_matches(text):
    """
    Finds matching files/directories in the specified path based on the prefix.
    Returns raw entry names relative to the directory searched.
    """
    # 1. Determine the target directory and the lookup prefix
    if '/' in text:
        # Split at the last slash
        dir_path, prefix = text.rsplit('/', 1)
        # Handle root directory edge case or append trailing slash for path evaluation
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
                # Ignore hidden files unless explicitly requested by prefix
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
    """
    Unified completion engine handling commands, relative/absolute file paths,
    LCP expansions, visual directory trailing slashes, and multi-tab lists.
    """
    if state == 0:
        # Read the entire raw line typed by the user so far
        line_buffer = readline.get_line_buffer()
        
        # Determine if we are completing the first command or a subsequent argument.
        # We strip trailing spaces to check if the user is starting a new argument.
        stripped_leading = line_buffer.lstrip()
        
        # If there are spaces in the buffer before our current token, it's an argument!
        is_argument = ' ' in stripped_leading
        
        if not is_argument:
            # --- Command Mode ---
            completer.raw_matches = get_command_matches(text)
            completer.mode = "command"
        else:
            # --- Filename Argument Mode ---
            completer.mode = "filename"
            # Get matches relative to the directory path being typed
            completer.raw_matches = get_filename_matches(text)

        if not completer.raw_matches:
            # Stage: Missing Entry Completions (Ring Bell)
            sys.stdout.write('\x07')
            sys.stdout.flush()
            return None

        # Process matching results
        if len(completer.raw_matches) > 1:
            # Calculate LCP based on raw entries discovered
            lcp_raw = longest_common_prefix(completer.raw_matches)
            
            # Reconstruct the full LCP token path to match against the typed input
            if completer.mode == "filename" and '/' in text:
                dir_part, _ = text.rsplit('/', 1)
                lcp_full = dir_part + '/' + lcp_raw
            else:
                lcp_full = lcp_raw

            # If the calculated LCP can expand what the user typed, complete up to it!
            if lcp_full and lcp_full != text:
                # Store a single-element list containing the LCP expansion
                completer.display_matches = [lcp_full]
                return lcp_full
            
            # If we can't expand text any further, ring the bell on the first tab press
            sys.stdout.write("\x07")
            sys.stdout.flush()

            # Pre-format the absolute presentation paths for readline to display to the user
            completer.display_matches = []
            for match in completer.raw_matches:
                # Reconstruct full path to check file stats accurately
                if completer.mode == "filename" and '/' in text:
                    dir_part, _ = text.rsplit('/', 1)
                    full_path = os.path.join(dir_part, match)
                    display_name = dir_part + '/' + match
                else:
                    full_path = match
                    display_name = match

                # Stage: Handling Multiple Matches formatting constraint
                if completer.mode == "filename" and os.path.isdir(full_path):
                    completer.display_matches.append(display_name + "/")
                else:
                    completer.display_matches.append(display_name)
        else:
            # Exactly 1 match found! Append trailing spaces or directory slashes
            single_match = completer.raw_matches[0]
            
            if completer.mode == "command":
                completer.display_matches = [single_match + " "]
            else:
                # Reconstruct path to check if it's a file or folder
                if '/' in text:
                    dir_part, _ = text.rsplit('/', 1)
                    full_path = os.path.join(dir_part, single_match)
                    completed_path = dir_part + '/' + single_match
                else:
                    full_path = single_match
                    completed_path = single_match

                # Stage: Directory Name Completion formatting constraint
                if os.path.isdir(full_path):
                    completer.display_matches = [completed_path + "/"]
                else:
                    completer.display_matches = [completed_path + " "]

    # Feed candidate values sequentially back to the Readline streaming loops
    if state < len(completer.display_matches):
        return completer.display_matches[state]
    return None

# Initialize memory cache attributes
completer.raw_matches = []
completer.display_matches = []
completer.mode = "command"

# --- Configure Readline Engine Hooks ---
readline.set_completer(completer)
if "libedit" in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")
else:
    readline.parse_and_bind("tab: complete")
    
# CRITICAL: Strip out forward slashes from the delimiter list!
# If '/' remains a delimiter, typing 'path/to/f' will slice text down to just 'f'
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
