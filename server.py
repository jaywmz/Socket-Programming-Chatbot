import socket
import threading

# Function to handle communication with a user
def handle_user(user_socket, users, user_names, groups):
    while True:
        try:
            # Receive message from the user
            message = user_socket.recv(1024).decode('utf-8')
            if message:
                if message.startswith("@quit"):
                    # Inform other users about the user quitting
                    broadcast(f"[{user_names[user_socket]} exited]", user_socket, users, user_names)
                    break
                elif message.startswith("@names"):
                    # Send list of connected users to the user
                    user_socket.sendall(f"[Connected users: {', '.join(user_names.values())}]".encode('utf-8'))
                elif message.startswith("@group set"):
                    create_group(message, user_socket, user_names, groups)
                elif message.startswith("@group send"):
                    send_group_message(message, user_socket, user_names, groups)
                elif message.startswith("@group delete"):
                    delete_group(message, user_socket, user_names, groups)
                elif message.startswith("@group leave"):
                    leave_group(message, user_socket, user_names, groups)
                elif message.startswith("@"):
                    # Handle personal messages
                    recipient_username, personal_message = parse_personal_message(message)
                    send_personal_message(recipient_username, personal_message, user_socket, user_names)
                else:
                    # Broadcast message to all users
                    broadcast(f"[{user_names[user_socket]}]: {message}", user_socket, users, user_names)
        except Exception as e:
            print(f"Error: {e}")
            break

    # Remove user from the list of users and close the socket
    users.remove(user_socket)
    user_socket.close()
    del user_names[user_socket]


# Function to create a group
def create_group(message, user_socket, user_names, groups):
    # Parse group name and members
    parts = message.split()[2:]
    group_name = parts[0]
    group_members = [member.strip() for member in ''.join(parts[1:]).split(',')]

    # Check if group name is alphanumeric
    if not group_name.isalnum():
        user_socket.sendall("[Group name must contain only alphanumeric characters]".encode('utf-8'))
        return

    # Check if group name already exists
    if group_name in groups:
        user_socket.sendall("[Group name already exists]".encode('utf-8'))
        return

    # Check if all members are valid
    for member in group_members:
        if member not in user_names.values():
            user_socket.sendall(f"[User '{member}' does not exist]".encode('utf-8'))
            return

    # Create the group
    groups[group_name] = group_members

    # Inform members about group creation
    for member in group_members:
        for socket, username in user_names.items():
            if username == member:
                socket.sendall(f"[You are enrolled in the {group_name} group]".encode('utf-8'))

# Function to send a message to a group
def send_group_message(message, user_socket, user_names, groups):
    # Parse group name and message
    parts = message.split()[2:]
    group_name = parts[0]
    group_message = ' '.join(parts[1:])

    # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Check if user is a member of the group
    if user_names[user_socket] not in groups[group_name]:
        user_socket.sendall("[You are not a member of this group]".encode('utf-8'))
        return

    # Send message to group members
    sender_name = user_names[user_socket]
    for member in groups[group_name]:
        for user_socket, username in user_names.items():
            if username == member.strip():
                # Differentiate group message based on sender
                if username == sender_name:
                    user_socket.sendall(f"[myself (group {group_name})]: {group_message}".encode('utf-8'))
                else:
                    user_socket.sendall(f"[{sender_name} (group {group_name})]: {group_message}".encode('utf-8'))

# Function to delete a group
def delete_group(message, user_socket, user_names, groups):
    # Parse group name
    group_name = message.split()[2]

    # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Check if user is the creator of the group
    if user_names[user_socket] != groups[group_name][0]:
        user_socket.sendall("[You are not authorized to delete this group]".encode('utf-8'))
        return

    # Inform group members about group deletion
    for member in groups[group_name]:
        for user_socket, username in user_names.items():
            if username == member:
                user_socket.sendall(f"[Group {group_name} has been deleted]".encode('utf-8'))

    # Delete the group
    del groups[group_name]

# Function to handle a user leaving a group
def leave_group(message, user_socket, user_names, groups):
    # Parse group name
    group_name = message.split()[2]

    # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Check if user is a member of the group
    if user_names[user_socket] not in groups[group_name]:
        user_socket.sendall("[You are not a member of this group]".encode('utf-8'))
        return

    # Inform all group members except the leaving member
    leaving_member = user_names[user_socket]
    for member_socket, member_username in user_names.items():
        if member_username != leaving_member and member_username in groups[group_name]:
            member_socket.sendall(f"[{leaving_member} has left the {group_name} group]".encode('utf-8'))

    # Remove user from the group if the user is in the group
    if leaving_member in groups[group_name]:
        groups[group_name].remove(leaving_member)

    # Inform user about leaving the group
    user_socket.sendall(f"[You have left the {group_name} group]".encode('utf-8'))


# Function to broadcast a message to all users except the sender
def broadcast(message, sender_socket, users, user_names):
    for user_socket in users:
        if user_socket != sender_socket:
            user_socket.sendall(message.encode('utf-8'))

# Function to parse personal messages
def parse_personal_message(message):
    recipient_username, personal_message = message.split(maxsplit=1)
    recipient_username = recipient_username[1:]  # Remove '@' symbol
    return recipient_username, personal_message


# Function to send a personal message to a specific user
def send_personal_message(recipient_username, personal_message, sender_socket, user_names):
    for user_socket, username in user_names.items():
        if username == recipient_username:
            user_socket.sendall(f"[Personal Message from {user_names[sender_socket]}]: {personal_message}".encode('utf-8'))
            break
        

# Main function to start the server
def main():
    host = 'localhost'
    port = 8888

    # Create a socket for the server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the host and port
    server_socket.bind((host, port))
    # Start listening for connections
    server_socket.listen(5)

    print(f"***Listening on {host}:{port}***")

    users = []
    user_names = {}
    groups = {}

    # Main loop to accept incoming connections
    while True:
        user_socket, addr = server_socket.accept()
        print(f"***Accepted connection from {addr[0]}:{addr[1]}***")

        # Prompt user for username
        while True:
            user_socket.sendall("Enter your username: ".encode('utf-8'))
            username = user_socket.recv(1024).decode('utf-8').strip()

            # Check if the username is already in use
            if username in user_names.values():
                # Inform user about duplicate username
                user_socket.sendall("[Existing Username. Please enter another name instead.]".encode('utf-8'))
            else:
                # Unique username, proceed
                user_names[user_socket] = username
                users.append(user_socket)

                # Welcome message for the new user
                user_socket.sendall(f"[Welcome {username}!]".encode('utf-8'))

                # Broadcast to other users that a new user has joined
                broadcast(f"[{username} joined]", user_socket, users, user_names)
                break

        # Start a new thread to handle communication with the user
        thread = threading.Thread(target=handle_user, args=(user_socket, users, user_names, groups))
        thread.start()

    # Close the server socket when the main loop ends
    server_socket.close()

if __name__ == "__main__":
    main()
