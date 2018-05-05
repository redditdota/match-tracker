import traceback, signal, sys
import atexit

def debug():
    message  = "Signal received, traceback:\n"
    message += ''.join(traceback.format_stack(frame))
    print(message)
    sys.stdout.flush()

def listen():
    signal.signal(signal.SIGUSR1, debug)  # Register handler
    atexit.register(debug)
