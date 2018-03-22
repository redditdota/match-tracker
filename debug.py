import traceback, signal

def debug(sig, frame):
    message  = "Signal received, traceback:\n"
    message += ''.join(traceback.format_stack(frame))
    print(message)

def listen():
    signal.signal(signal.SIGUSR1, debug)  # Register handler
