import socket
import threading

users = []

# Function to handle communication with a user
def handle_user(user_socket, user_names, groups):
    global users
    users.append(user_socket)
    commands = {
        "@quit": quit_command,
        "@names": names,
        "@group set": create_group,
        "@group send": send_group_message,
        "@group delete": delete_group,
        "@group leave": leave_group,
        "@group add": add_group_member,
        "@group list": list_groups,
        "@group members": list_group_members,
        "@group remove": remove_group_member,
    }

    try:
        while True:
            message = user_socket.recv(1024).decode('utf-8').strip()
            if not message:
                continue

            # Split the message for initial command detection
            parts = message.split(' ', 2)
            command = parts[0]

            # Handling group commands as a special case
            if command == "@group" and len(parts) > 1:
                # Reconstruct the group command with its specific action
                group_command = " ".join(parts[:2])
                if group_command in commands:
                    commands[group_command](message, user_socket, user_names, groups)
                else:
                    user_socket.sendall("Invalid group command. Please check your syntax.".encode('utf-8'))
                continue

            # Handling predefined commands excluding group commands
            if command in commands and command != "@group":
                commands[command](message, user_socket, user_names, groups)
                continue

            # Handling private messages
            if command.startswith("@") and len(parts) == 2:
                recipient_username, personal_message = parts[0][1:], parts[1]
                if recipient_username in user_names.values():
                    send_personal_message(recipient_username, personal_message, user_socket, user_names)
                else:
                    user_socket.sendall(f"User '{recipient_username}' does not exist.".encode('utf-8'))
            else:
                # Broadcast non-command messages to all users
                broadcast(message, user_socket, user_names)

    except OSError as e:
        print(f"Socket error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cleanup_user(user_socket, user_names, groups)




def cleanup_user(user_socket, user_names, groups):
    global users
    # Attempt to get the username; default to 'Unknown user' if not found.
    username = user_names.get(user_socket, 'Unknown user')
    
    # Safely attempt to close the user socket.
    try:
        user_socket.close()
    except OSError as e:
        print(f"Error closing socket: {e}")
    
    # Ensure that operations on shared resources are thread-safe.
    try:
        if user_socket in users:
            users.remove(user_socket)
        if user_socket in user_names:
            del user_names[user_socket]

        # Broadcast user's exit after removing from lists to prevent sending to closed socket.
        broadcast(f"[{username} exited]", None, user_names)  # Pass None as sender_socket since it's closed.
        
        # Remove the user from all groups they are a part of.
        for group_name, group_members in groups.items():
            if username in group_members:
                group_members.remove(username)
                # Optional: Broadcast to the group that the user has left, if desired.
    except Exception as e:
        print(f"Error during cleanup: {e}")



def quit_command(message, user_socket, user_names, groups):
    # Retrieve the username of the user who is quitting
    username = user_names.get(user_socket, 'Unknown user')

    # Broadcast the user's exit message to all other users, using is_join_message=True to avoid prefix
    broadcast(f"[{username} exited]", sender_socket=user_socket, user_names=user_names, is_join_message=True)

    # Perform cleanup for the user who is quitting
    cleanup_user(user_socket, user_names, groups)

    # Close the user's socket
    try:
        user_socket.close()
    except OSError as e:
        print(f"Error closing socket for {username}: {e}")

    print(f"{username} has quit the chat.")



def names(message, user_socket, user_names, groups):
    # Create a list of all connected users
    connected_users = [username for username in user_names.values()]
    # Send the list to the user
    user_socket.sendall(f"Connected users: {', '.join(connected_users)}".encode('utf-8'))

# Function to create a group
def create_group(message, user_socket, user_names, groups):
    # Parse group name and members
    parts = message.split()[2:]
    if len(parts) < 2:
        user_socket.sendall("[Invalid input. Please provide a group name and at least one member.]".encode('utf-8'))
        return
    
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
    
    # Check if the necessary parameters are present
    if len(parts) < 2:
        user_socket.sendall("[Invalid input. Please provide a group name and a message.]".encode('utf-8'))
        return
    
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
    parts = message.split(maxsplit=3)
    # Expected parts: ['@group', 'leave', 'group_name', 'optional_username']

    # Validate the command structure
    if len(parts) < 3:
        user_socket.sendall("[Invalid input. Please provide a group name.]".encode('utf-8'))
        return

    group_name = parts[2]
    specified_username = parts[3] if len(parts) == 4 else user_names[user_socket]

    # Authority check (optional)
    # This example does not implement authority check; assuming all users can remove themselves or specified users

    # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Check if the specified user is a member of the group
    if specified_username not in groups[group_name]:
        user_socket.sendall(f"[{specified_username} is not a member of {group_name} group.]".encode('utf-8'))
        return

    # Remove the specified user from the group
    groups[group_name].remove(specified_username)

    # Inform the group about the user leaving
    message_to_group = f"[{specified_username} has left the {group_name} group]"
    for member_socket, member_username in user_names.items():
        if member_username in groups[group_name] or member_username == specified_username:
            member_socket.sendall(message_to_group.encode('utf-8'))

    # Inform the user who issued the command about the successful operation
    if specified_username == user_names[user_socket]:
        user_socket.sendall(f"[You have left the {group_name} group]".encode('utf-8'))
    else:
        user_socket.sendall(f"[{specified_username} has been removed from the {group_name} group]".encode('utf-8'))

    # Optional: Delete the group if it's empty
    if not groups[group_name]:
        del groups[group_name]
        # Inform the server or log the deletion
        print(f"The {group_name} group has been deleted because it became empty.")




# Function to delete a group
def delete_group(message, user_socket, user_names, groups):
    # Parse group name
    parts = message.split()[2:]
    
    # Check if the necessary parameters are present
    if len(parts) < 1:
        user_socket.sendall("[Invalid input. Please provide a group name.]".encode('utf-8'))
        return

    group_name = parts[0]

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
    
    # Check if the necessary parameters are present
    if len(parts) < 2:
        user_socket.sendall("[Invalid input. Please provide a group name and at least one member to add.]".encode('utf-8'))
        return
    
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

    # Check if the necessary parameters are present
    if len(parts) < 2:
        user_socket.sendall("[Invalid input. Please provide a group name and at least one member to remove.]".encode('utf-8'))
        return
    
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
    # Parse group name
    parts = message.split()

    # Check if the necessary parameters are present
    if len(parts) < 3:
        user_socket.sendall("[Invalid input. Please provide a group name.]".encode('utf-8'))
        return

    group_name = parts[2]
    
    if group_name in groups:
        group_members = groups[group_name]
        user_socket.sendall(f"[Members in {group_name} group: {', '.join(group_members)}]".encode('utf-8'))
    else:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        
# Function to broadcast a message to all users except the sender
def broadcast(message, sender_socket, user_names, is_join_message=False):
    for user in users:
        if user is not sender_socket:
            if is_join_message:
                user.sendall(f"{message}".encode('utf-8'))
            else:
                user.sendall(f"[{user_names[sender_socket]}]: {message}".encode('utf-8'))

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
def handle_server_commands(server_socket, users, user_names, groups):
    while True:
        command = input("Server command: ")
        if command.strip().lower() == "@quit":
            print("Shutting down the server...")

            # Inform all connected clients about server shutting down
            for user_socket in list(users):  # Use a copy of the list to avoid modification during iteration
                try:
                    # Safely attempt to notify the client and close the socket.
                    user_socket.sendall("[Server is shutting down]".encode('utf-8'))
                    cleanup_user(user_socket, user_names, groups)
                except OSError as e:
                    print(f"Error sending shutdown message to a client: {e}")
            print("All clients have been notified and disconnected.")

            # Close the server socket to stop accepting new connections.
            try:
                server_socket.close()
            except OSError as e:
                print(f"Error closing server socket: {e}")

            print("Server has been successfully shut down.")
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
    command_thread = threading.Thread(target=handle_server_commands, args=(server_socket, users, user_names, groups))
    command_thread.start()

    # Main loop to accept incoming connections
    while True:
        try:
            user_socket, addr = server_socket.accept()
            print(f"***Accepted connection from {addr[0]}:{addr[1]}***")
        except OSError as e:
            print(f"Error: {e}")
            break

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
                broadcast(f"[{username} joined]", user_socket, user_names, is_join_message=True)
                break

        # Start a new thread to handle communication with the user
        thread = threading.Thread(target=handle_user, args=(user_socket, user_names, groups))
        thread.start()

if __name__ == "__main__":
    main()
