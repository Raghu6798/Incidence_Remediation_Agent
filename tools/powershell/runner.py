# file: tools/powershell/runner.py

import subprocess
import threading
import uuid
import queue

class PowerShellRunner:
    """
    A persistent PowerShell session runner that uses dedicated threads to read
    stdout and stderr, preventing deadlocks.
    """
    def __init__(self):
        self.process = subprocess.Popen(
            ["powershell.exe", "-NoExit", "-NoLogo", "-Command", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            bufsize=1
        )
        self.lock = threading.Lock()

        # --- Threaded Stream Reading Setup ---
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()

        self.stdout_thread = threading.Thread(target=self._enqueue_output, args=(self.process.stdout, self.stdout_queue))
        self.stderr_thread = threading.Thread(target=self._enqueue_output, args=(self.process.stderr, self.stderr_queue))
        
        # Daemon threads will exit when the main program exits
        self.stdout_thread.daemon = True
        self.stderr_thread.daemon = True
        
        self.stdout_thread.start()
        self.stderr_thread.start()

    def _enqueue_output(self, pipe, q):
        """Reads lines from a pipe and puts them into a queue."""
        for line in iter(pipe.readline, ''):
            q.put(line)
        pipe.close()

    def run_command(self, command: str, timeout: int = 120) -> dict:
        """
        Runs a command in the persistent PowerShell session.
        Returns a dictionary with stdout, stderr, and a heuristic return code.
        """
        with self.lock:
            end_marker = f"END_OF_COMMAND_{uuid.uuid4()}"
            # This command structure writes the marker to both streams
            # to signal completion on both ends.
            full_command = f"""
$ProgressPreference = 'SilentlyContinue'
{command}
if ($?) {{ $LAST_EXIT_CODE = 0 }} else {{ $LAST_EXIT_CODE = 1 }}
Write-Output "{end_marker} EXIT_CODE:$LAST_EXIT_CODE"
Write-Error "{end_marker} EXIT_CODE:$LAST_EXIT_CODE"
"""
            
            self.process.stdin.write(full_command + "\n")
            self.process.stdin.flush()
            
            stdout_lines = []
            stderr_lines = []
            
            # Read from queues until both markers are found or timeout
            # This is a much safer way to read from both streams.
            end_stdout = False
            end_stderr = False
            
            while not (end_stdout and end_stderr):
                try:
                    # Non-blocking get from the queue
                    stdout_line = self.stdout_queue.get_nowait()
                    if end_marker in stdout_line:
                        end_stdout = True
                    else:
                        stdout_lines.append(stdout_line)
                except queue.Empty:
                    pass # No new stdout line

                try:
                    stderr_line = self.stderr_queue.get_nowait()
                    if end_marker in stderr_line:
                        end_stderr = True
                    else:
                        stderr_lines.append(stderr_line)
                except queue.Empty:
                    pass # No new stderr line
                
                # If both streams have signaled the end, we can stop.
                if end_stdout and end_stderr:
                    break
            
            stdout = "".join(stdout_lines)
            stderr = "".join(stderr_lines)
            
            # Basic heuristic for return code. A real implementation might parse it.
            returncode = 1 if "Error:" in stderr or "failed" in stderr.lower() else 0
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode
            }

    def close(self):
        """Closes the PowerShell process and waits for it to terminate."""
        if self.process and self.process.poll() is None:
            with self.lock:
                try:
                    self.process.stdin.write("exit\n")
                    self.process.stdin.flush()
                except (IOError, BrokenPipeError):
                    # The process might have already closed, which is fine.
                    pass
                finally:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()