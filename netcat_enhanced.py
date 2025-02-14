import socket
import argparse
import threading
import sys
import os
import ssl  # For SSL support

def handle_client(client_socket, args):
    """Handles communication with a single client."""
    try:
        if args.execute:
            output = run_command(args.execute)
            client_socket.sendall(output.encode()) #Send result of command
        elif args.upload:
            file_buffer = ""
            while True:
                data = client_socket.recv(4096).decode()
                if not data:
                    break
                file_buffer += data

            try:
                with open(args.upload, "wb") as f:
                    f.write(file_buffer.encode())
                client_socket.sendall(b"File uploaded successfully.\n") # Send confirmation
            except Exception as e:
                client_socket.sendall(f"Error uploading file: {e}\n".encode())

        elif args.command:
            while True:
                client_socket.sendall(b"netcat-enhanced> ")  # Custom prompt
                cmd = client_socket.recv(4096).decode().strip()
                if cmd in ["exit", "quit"]:
                    break
                if cmd: # Don't execute empty commands
                    output = run_command(cmd)
                    client_socket.sendall(output.encode())

        # Interactive shell (default)
        else:
            while True:
                data = client_socket.recv(4096).decode()
                if not data:
                    break
                sys.stdout.write(data)  # Print received data to stdout
                if sys.stdin.isatty():  # Only prompt if stdin is a TTY
                    client_socket.sendall(sys.stdin.readline().encode())

    except Exception as e:
        print(f"Client handler error: {e}")
    finally:
        client_socket.close()

def run_command(command):
    """Executes a command and returns its output."""
    try:
        output = os.popen(command).read()
        return output
    except Exception as e:
        return f"Error executing command: {e}\n"

def server(args):
    """Starts the server."""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((args.listen, args.port))
        server_socket.listen(5)  # Increased backlog
        print(f"Listening on {args.listen}:{args.port}")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr[0]}:{addr[1]}")

            if args.ssl:  # Wrap the socket for SSL if enabled
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                if args.certfile and args.keyfile: # Load certificate and key
                    context.load_cert_chain(certfile=args.certfile, keyfile=args.keyfile)
                else:
                    print("SSL enabled but no certificate or key provided. Using default context (may not be secure).")

                client_socket = context.wrap_socket(client_socket, server_side=True)

            client_thread = threading.Thread(target=handle_client, args=(client_socket, args))
            client_thread.start()

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()

def client(args):
    """Starts the client."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((args.target, args.port))

        if args.ssl:
            context = ssl.create_default_context() # Client context
            client_socket = context.wrap_socket(client_socket, server_hostname=args.target) # Wrap with SSL

        handle_client(client_socket, args) # Use same handler

    except Exception as e:
        print(f"Client error: {e}")
    finally:
        client_socket.close()

def main():
    parser = argparse.ArgumentParser(description="Enhanced Netcat (netcat-enhanced)")

    parser.add_argument("-l", "--listen", default="0.0.0.0", help="Listen IP (server)")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Port")
    parser.add_argument("-t", "--target", default="127.0.0.1", help="Target IP (client)")
    parser.add_argument("-e", "--execute", help="Execute command")
    parser.add_argument("-u", "--upload", help="Upload file")
    parser.add_argument("-c", "--command", action="store_true", help="Start command shell")
    parser.add_argument("-s", "--ssl", action="store_true", help="Enable SSL")
    parser.add_argument("--certfile", help="Path to SSL certificate file")
    parser.add_argument("--keyfile", help="Path to SSL private key file")

    args = parser.parse_args()

    if args.listen:
        server(args)
    else:
        client(args)

if __name__ == "__main__":
    main()
