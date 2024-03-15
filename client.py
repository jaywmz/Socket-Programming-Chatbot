import socket
import threading

# Function to continuously receive messages from the server
def receive_messages(user_socket):
    while True:
        try:
            # Receive message from server
            message = user_socket.recv(1024).decode('utf-8')
            # Print received message
            print(message)
        except Exception as e:
            # Print error if any
            print(f"Error: {e}")
            break

# Main function for the user
def main():
    
    while True:
        try:
            # Get server configuration from user
            host = input("Enter the server IP address: ")
            port = int(input("Enter the server port number: "))

            # Create a socket for the user
            user_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect to the server
            user_socket.connect((host, port))
            break  # If connection is successful, break the loop
        except Exception as e:
            print("Error connecting to server. Please check the server IP and port number and try again.")
            print("Error details:", e)

    # Receive and print welcome message from the server
    welcome_message = user_socket.recv(1024).decode('utf-8')
    print(welcome_message)

    # Start a thread to receive messages from the server continuously
    thread = threading.Thread(target=receive_messages, args=(user_socket,))
    thread.start()

    # Main loop for sending messages to the server
    while True:
        # Get user input
        message = input()

        try:
            # Send "@quit" command to disconnect from the server
            if message == "@quit":
                user_socket.sendall(message.encode('utf-8'))
                break
            # Send "@names" command to get list of connected users
            elif message == "@names":
                user_socket.sendall(message.encode('utf-8'))
            else:
                # Send user's message to the server
                user_socket.sendall(message.encode('utf-8'))
        except ConnectionResetError:
            print("Connection was closed by the server.")
            break

    # Close the user socket
    user_socket.close()

if __name__ == "__main__":
    main()