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
                elif message.startswith("@group add"):
                    add_group_member(message, user_socket, user_names, groups)
                elif message.startswith("@group list"):
                    list_groups(message, user_socket, user_names, groups)
                elif message.startswith("@group members"):
                    list_group_members(message, user_socket, user_names, groups)
                elif message.startswith("@group remove"):
                    remove_group_member(message, user_socket, user_names, groups)
                elif message.startswith("@"):
                    # Handle personal messages
                    recipient_username, personal_message = parse_personal_message(message)
                    send_personal_message(recipient_username, personal_message, user_socket, user_names)
                else:
                    # Broadcast message to all users
                    broadcast(f"[{user_names[user_socket]}]: {message}", user_socket, users, user_names)
        except Exception as e:
            # Log the error and continue listening for messages
            user_socket.sendall("[Invalid input. Please try again.]".encode('utf-8'))
            continue

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
    sender_name = user_names[user_socket]

    if len(group_members) == 1 and sender_name in group_members:
        user_socket.sendall(f"[You enrolled yourself into {group_name} group]".encode('utf-8'))
    else:
        for member in group_members:
            for socket, username in user_names.items():
                if username == member:
                    if member != sender_name:
                        socket.sendall(f"[You are enrolled.{sender_name} added you to the {group_name} group]".encode('utf-8'))
                    else:
                        if sender_name in group_members:
                            socket.sendall(f"[You enrolled yourself and {' '.join([m for m in group_members if m != sender_name])} into the {group_name} group]".encode('utf-8'))
                        else:
                            socket.sendall(f"[{sender_name} added {', '.join(group_members)} to the {group_name} group]".encode('utf-8'))


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


# Function to delete a group
def delete_group(message, user_socket, user_names, groups):
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

    # Prompt the user if they want to delete the group
    user_socket.sendall(f"[Do you want to delete the group '{group_name}'? This action will remove all members. (yes/no):] ".encode('utf-8'))
    response = user_socket.recv(1024).decode('utf-8').strip()

    if response.lower() == 'no':
        user_socket.sendall("[Group deletion cancelled]".encode('utf-8'))
        return
    elif response.lower() != 'yes':
        user_socket.sendall("[Invalid response. Group deletion cancelled]".encode('utf-8'))
        return

    # Inform group members about group deletion
    creator_message = f"[You have removed all members from {group_name}, {group_name} has been deleted.]"
    member_message = f"[You have been removed from {group_name}, {group_name} has been deleted.]"

    for member in groups[group_name]:
        for member_socket, username in user_names.items():
            if username == member:
                if member_socket == user_socket:
                    member_socket.sendall(creator_message.encode('utf-8'))
                else:
                    member_socket.sendall(member_message.encode('utf-8'))

    # Delete the group
    del groups[group_name]



# Function to add a member to a group
def add_group_member(message, user_socket, user_names, groups):
    # Parse group name and member(s) to add
    parts = message.split()[2:]
    group_name = parts[0]
    members_to_add = [member.strip() for member in ''.join(parts[1:]).split(',')]

    # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Check if any member to add is already in the group
    existing_members = groups[group_name]
    already_members = [member for member in members_to_add if member in existing_members]
    if already_members:
        user_socket.sendall(f"[{', '.join(already_members)} already member(s) of this group]".encode('utf-8'))
        return

    # Check if all members to add exist
    non_existing_members = [member for member in members_to_add if member not in user_names.values()]
    if non_existing_members:
        user_socket.sendall(f"[User(s) {' '.join(non_existing_members)} to add do(es) not exist]".encode('utf-8'))
        return

    # Add members to the group
    groups[group_name].extend(members_to_add)

    # Inform the added members
    sender_name = user_names[user_socket]
    for member_socket, member_username in user_names.items():
        if member_username in members_to_add:
            member_socket.sendall(f"[You are enrolled.{sender_name} added you to the {group_name} group]".encode('utf-8'))

    # Inform the user who added the members
    if len(members_to_add) == 1 and members_to_add[0] == sender_name:
        user_socket.sendall(f"[You enrolled yourself into the {group_name} group]".encode('utf-8'))
    else:
        user_socket.sendall(f"[You enrolled {' '.join(members_to_add)} into the {group_name} group]".encode('utf-8'))

    # Inform the remaining group members about the addition
    for member_socket, member_username in user_names.items():
        if member_username not in members_to_add and member_username in groups[group_name] and member_socket != user_socket:
            member_socket.sendall(f"[{' '.join(members_to_add)} were added to the {group_name} group by {sender_name}]".encode('utf-8'))



# Function to remove member(s) from a group
def remove_group_member(message, user_socket, user_names, groups):
    # Parse group name and member(s) to remove
    parts = message.split()[2:]
    group_name = parts[0]
    members_to_remove = [member.strip() for member in ''.join(parts[1:]).split(',')]

    # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Remove members from the group and handle invalid usernames
    removed_members = []
    for member in members_to_remove:
        if member in groups[group_name]:
            groups[group_name].remove(member)
            removed_members.append(member)
        else:
            user_socket.sendall(f"[Error]: '{member}' is not a member of the {group_name} group.".encode('utf-8'))

    # Inform the removed members
    sender_name = user_names[user_socket]
    for member_socket, member_username in user_names.items():
        if member_username in removed_members:
            member_socket.sendall(f"[{sender_name} removed you from the {group_name} group]".encode('utf-8'))

    # Inform the user who removed the members
    if removed_members:
        user_socket.sendall(f"[You removed {' '.join(removed_members)} from the {group_name} group]".encode('utf-8'))
    else:
        user_socket.sendall("[No members were removed from the group]".encode('utf-8'))

    # Inform the remaining group members about the removal
    for member_socket, member_username in user_names.items():
        if member_username in groups[group_name] and member_socket != user_socket:
            member_socket.sendall(f"[{', '.join(removed_members)} were removed from the {group_name} group by {sender_name}]".encode('utf-8'))



# Function to list all groups a user is in
def list_groups(message, user_socket, user_names, groups):
    username = user_names[user_socket]
    user_groups = [group_name for group_name, group_members in groups.items() if username in group_members]
    if user_groups:
        user_socket.sendall(f"[Groups you are in: {', '.join(user_groups)}]".encode('utf-8'))
    else:
        user_socket.sendall("[You are not in any groups]".encode('utf-8'))

# Function to list all members in a group
def list_group_members(message, user_socket, user_names, groups):
    group_name = message.split()[2]
    if group_name in groups:
        group_members = groups[group_name]
        user_socket.sendall(f"[Members in {group_name} group: {', '.join(group_members)}]".encode('utf-8'))
    else:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        
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
    recipient_socket = None
    for user_socket, username in user_names.items():
        if username == recipient_username:
            recipient_socket = user_socket
            break

    if recipient_socket is None:
        sender_socket.sendall(f"[Error]: User '{recipient_username}' does not exist.".encode('utf-8'))
    else:
        recipient_socket.sendall(f"[Personal Message from {user_names[sender_socket]}]: {personal_message}".encode('utf-8'))
        
# Function to handle server commands
def handle_server_commands(server_socket, users, user_names):
    while True:
        command = input()
        if command.startswith("@quit"):
            # Inform all connected clients about server shutting down
            for user_socket in users:
                user_socket.sendall("[Server is shutting down]".encode('utf-8'))
            # Close all client connections
            for user_socket in users:
                user_socket.close()
            # Close the server socket
            server_socket.close()
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

    # Start a thread to handle server commands
    command_thread = threading.Thread(target=handle_server_commands, args=(server_socket, users, user_names))
    command_thread.start()

    # Main loop to accept incoming connections
    while True:
        user_socket, addr = server_socket.accept()
        print(f"***Accepted connection from {addr[0]}:{addr[1]}***")

        # Prompt user for username
        while True:
            user_socket.sendall("Enter your username: ".encode('utf-8'))
            username = user_socket.recv(1024).decode('utf-8').strip()

            # Convert username to lowercase
            username_lower = username.lower()

            # Check if the username is already in use
            if username_lower in map(str.lower, user_names.values()):
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

if __name__ == "__main__":
    main()
