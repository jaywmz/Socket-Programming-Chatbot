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
        "@group remove": remove_group_member,
        "@group members": list_group_members,
        "@group authorize": authorize_group_member,
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
            # Handling personal messages
            # Handling private messages
            if message.startswith("@") and not message.startswith("@group"):
                # Find the first space or the end of the message
                space_index = message.find(' ')
                if space_index == -1:
                    space_index = len(message)

                # Extract the username and the message
                recipient_username = message[1:space_index]
                personal_message = message[space_index:].strip()

                if recipient_username in [name for socket, name in user_names.items()]:  # Check if recipient exists
                    send_personal_message(recipient_username, personal_message, user_socket, user_names)
                else:
                    user_socket.sendall(f"User '{recipient_username}' does not exist.".encode('utf-8'))
            else:
                # For messages that are not personal or commands, broadcast to all users
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

    
    # Create the group with members and admins
    creator_username = user_names[user_socket]
    groups[group_name] = {'members': [member for member in group_members if member != creator_username], 'admins': [creator_username]}

    # Inform members about group creation
    if len(group_members) == 1 and group_members[0] == creator_username:
        user_socket.sendall(f"[You created the {group_name} group]".encode('utf-8'))
    else:
        for member in group_members:
            for socket, username in user_names.items():
                if username == member:
                    if member != creator_username:
                        socket.sendall(f"[You are enrolled into the {group_name} group by {creator_username}]".encode('utf-8'))
                    else:
                        socket.sendall(f"[You created the {group_name} group and added {', '.join(group_members)}]".encode('utf-8'))


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
    sender_username = user_names[user_socket]
    if sender_username not in groups[group_name]['members'] and sender_username not in groups[group_name]['admins']:
        user_socket.sendall("[You are not a member of this group]".encode('utf-8'))
        return

    # Send message to group members
    for member_socket, member_username in user_names.items():
        if member_username in groups[group_name]['members']:
            if member_username == sender_username:
                member_socket.sendall(f"[myself (group {group_name})]: {group_message}".encode('utf-8'))
            else:
                member_socket.sendall(f"[{sender_username} (group {group_name})]: {group_message}".encode('utf-8'))
    
     # Send message to group members
    for member_socket, member_username in user_names.items():
        if member_username in groups[group_name]['admins']:
            if member_username == sender_username:
                member_socket.sendall(f"[myself (group {group_name})]: {group_message}".encode('utf-8'))
            else:
                member_socket.sendall(f"[{sender_username} (group {group_name})]: {group_message}".encode('utf-8'))

# Function to handle a user leaving a group
def leave_group(message, user_socket, user_names, groups):
    parts = message.split(maxsplit=3)

    # Validate the command structure
    if len(parts) < 3:
        user_socket.sendall("[Invalid input. Please provide a group name.]".encode('utf-8'))
        return

    group_name = parts[2]
    # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Check if user is a member of the group
    leaving_member = user_names[user_socket]
    if leaving_member not in groups[group_name]['members'] and leaving_member not in groups[group_name]['admins']:
        user_socket.sendall("[You are not a member of this group]".encode('utf-8'))
        return

    # Remove user from the group if the user is in the group
    if leaving_member in groups[group_name]['members']:
        groups[group_name]['members'].remove(leaving_member)
    if leaving_member in groups[group_name]['admins']:
        groups[group_name]['admins'].remove(leaving_member)

    # Check if the group still exists after the member leaves
    if not groups[group_name]['members'] and not groups[group_name]['admins']:
        del groups[group_name]
        user_socket.sendall(f"[The {group_name} group has been deleted because all members have left]".encode('utf-8'))
        return
    
    # If the leaving member is the last admin
    if not groups[group_name]['admins'] and groups[group_name]['members']:
        
        if len(groups[group_name]['members']) == 1:  # If only one member left
            new_admin = groups[group_name]['members'][0]
            groups[group_name]['admins'].append(new_admin)
            groups[group_name]['members'].remove(new_admin)
            for member_socket, member_username in user_names.items():
                if member_username == new_admin:
                    member_socket.sendall(f"[You have been assigned as an admin of the {group_name} group because you are the only member left]".encode('utf-8'))
        
        elif len(groups[group_name]['members']) > 1:  # If more than one member left
            user_socket.sendall(f"Do you want to assign an admin from the remaining members? (yes/no): ".encode('utf-8'))
            response = user_socket.recv(1024).decode('utf-8').strip()
            
            if response.lower() == 'yes':
                remaining_members = groups[group_name]['members']
                user_socket.sendall(f"Remaining members: {', '.join(remaining_members)}\nChoose a member to assign as admin: ".encode('utf-8'))
                admin_choice = user_socket.recv(1024).decode('utf-8').strip()
                
                if admin_choice in remaining_members:
                    groups[group_name]['admins'].append(admin_choice)
                    groups[group_name]['members'].remove(admin_choice)
                    for member_socket, member_username in user_names.items():
                        if member_username == admin_choice:
                            member_socket.sendall(f"[You have been assigned as an admin of the {group_name} group]".encode('utf-8'))
                            break  
                    # Send notification to other members
                    for member_socket, member_username in user_names.items():
                        if member_username not in groups[group_name]['admins'] and member_username != admin_choice:
                            member_socket.sendall(f"[{admin_choice} has been assigned as an admin of the {group_name} group]".encode('utf-8'))
                            
                else:
                    auto_assigned_admin = groups[group_name]['members'][0]
                    groups[group_name]['admins'].append(auto_assigned_admin)
                    groups[group_name]['members'].remove(auto_assigned_admin) 
                    for member_socket, member_username in user_names.items():
                        if member_username == auto_assigned_admin:
                            member_socket.sendall(f"[You have been auto-assigned as an admin of the {group_name} group]".encode('utf-8'))
                            break  
                    # Send notification to other members
                    for member_socket, member_username in user_names.items():
                        if member_username not in groups[group_name]['admins'] and member_username != auto_assigned_admin:
                            member_socket.sendall(f"[{auto_assigned_admin} has been auto-assigned as an admin of the {group_name} group]".encode('utf-8'))
                            
            else:
                auto_assigned_admin = groups[group_name]['members'][0]
                groups[group_name]['admins'].append(auto_assigned_admin)
                groups[group_name]['members'].remove(auto_assigned_admin) 
                for member_socket, member_username in user_names.items():
                    if member_username == auto_assigned_admin:
                        member_socket.sendall(f"[You have been auto-assigned as an admin of the {group_name} group]".encode('utf-8'))
                        break  
                # Send notification to other members
                for member_socket, member_username in user_names.items():
                    if member_username not in groups[group_name]['admins'] and member_username != auto_assigned_admin:
                        member_socket.sendall(f"[{auto_assigned_admin} has been auto-assigned as an admin of the {group_name} group]".encode('utf-8'))
    
    # Inform all group members except the leaving member and the previously left admin
    for member_socket, member_username in user_names.items():
        if member_username != leaving_member:
            member_socket.sendall(f"[{leaving_member} has left the {group_name} group]".encode('utf-8'))

    # Inform user about leaving the group
    user_socket.sendall(f"[You have left the {group_name} group]".encode('utf-8'))
    
    # Remove the leaving member's socket from user_names
    # del user_names[user_socket]

    
def delete_group(message, user_socket, user_names, groups):
    # Parse group name
    parts = message.split()[2:]
    
    # Check if the necessary parameters are present
    if len(parts) < 1:
        user_socket.sendall("[Invalid input. Please provide a group name.]".encode('utf-8'))
        return

    group_name = parts[0]
    members_to_add = [member.strip() for member in ''.join(parts[1:]).split(',')]

     # Check if group exists
    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    # Check if user is the creator or an admin of the group
    user_username = user_names[user_socket]
    if user_username not in groups[group_name]['admins']:
        user_socket.sendall("[You are not authorized to delete this group]".encode('utf-8'))
        return

    # Prompt the creator/admin if they want to delete the group
    user_socket.sendall(f"Do you want to delete the group '{group_name}'? This action will remove all members. (yes/no): ".encode('utf-8'))
    response = user_socket.recv(1024).decode('utf-8').strip()

    if response.lower() == 'no':
        user_socket.sendall("[Group deletion cancelled]".encode('utf-8'))
        return
    elif response.lower() != 'yes':
        user_socket.sendall("[Invalid response. Group deletion cancelled]".encode('utf-8'))
        return

    # Inform admin about group deletion
    admin_message = f"You have deleted the group '{group_name}'."
    deletion_message = f"The group '{group_name}' has been deleted by {user_username}."

    for member in groups[group_name]['members'] + groups[group_name]['admins']:
        for member_socket, username in user_names.items():
            if username == member:
                if member_socket == user_socket:
                    member_socket.sendall(admin_message.encode('utf-8'))
                elif username != user_username:
                    member_socket.sendall(deletion_message.encode('utf-8'))

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

    # Check if user is the creator or an admin of the group
    sender_name = user_names[user_socket]
    if sender_name not in groups[group_name]['admins']:
        user_socket.sendall("[You are not authorized to add members to this group]".encode('utf-8'))
        return

    # Check if any member to add is already in the group
    existing_members = groups[group_name]['members'] + groups[group_name]['admins']
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
    groups[group_name]['members'].extend(members_to_add)

    # Inform the added members
    for member_socket, member_username in user_names.items():
        if member_username in members_to_add:
            member_socket.sendall(f"[You are enrolled into the {group_name} group by {sender_name}]".encode('utf-8'))

    # Inform user that added members about the addition
    user_socket.sendall(f"[You added {' '.join(members_to_add)} to the {group_name} group]".encode('utf-8'))

    # Inform other members and admins about the addition
    for member_socket, member_username in user_names.items():
        if member_username != sender_name and member_username not in members_to_add and (member_username in groups[group_name]['members'] or member_username in groups[group_name]['admins']):
            member_socket.sendall(f"[{', '.join(members_to_add)} were added to the {group_name} group by {sender_name}]".encode('utf-8'))



# Function to remove member(s) from a group
def remove_group_member(message, user_socket, user_names, groups):
    parts = message.split()[2:]

    if len(parts) < 2:
        user_socket.sendall("[Invalid input. Please provide a group name and at least one member to remove.]".encode('utf-8'))
        return

    group_name = parts[0]
    members_to_remove = [member.strip() for member in ''.join(parts[1:]).split(',')]

    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    if user_names[user_socket] not in groups[group_name]['admins']:
        user_socket.sendall("[You are not authorized to remove members from this group]".encode('utf-8'))
        return

    # Combined members and admins for the removal check
    existing_members = groups[group_name]['members'] + groups[group_name]['admins']
    
    for member in members_to_remove:
        # Check if member is in the group (either as member or admin)
        if member not in existing_members:
            user_socket.sendall(f"[{member} is not a member of the {group_name} group]".encode('utf-8'))
            continue  # Skip to the next member

        # Handle removing from members list if present
        if member in groups[group_name]['members']:
            groups[group_name]['members'].remove(member)

        # Handle removing from admins list if present
        if member in groups[group_name]['admins']:
            groups[group_name]['admins'].remove(member)
            # Optionally, demote to a regular member instead of removing from the group entirely
            # groups[group_name]['members'].append(member)

        # Inform the removed member
        for member_socket, member_username in user_names.items():
            if member_username == member:
                member_socket.sendall(f"[You have been removed from the {group_name} group by {user_names[user_socket]}]".encode('utf-8'))

    # Inform the user who removed the members
    user_socket.sendall(f"[You removed {' '.join(members_to_remove)} from the {group_name} group]".encode('utf-8'))

    # Inform the remaining group members and admins about the removal
    for member_socket, member_username in user_names.items():
        if member_username in existing_members and member_username != user_names[user_socket]:
            member_socket.sendall(f"[{' '.join(members_to_remove)} were removed from the {group_name} group by {user_names[user_socket]}]".encode('utf-8'))



# Function to list all groups a user is in
def list_groups(message, user_socket, user_names, groups):
    username = user_names[user_socket]
    user_groups = [group_name for group_name, group_data in groups.items() if username in group_data['members'] or username in group_data['admins']]
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
        group_members = groups[group_name]['members']
        admins = groups[group_name]['admins']
        formatted_members = [f"{member}" if member in admins else member for member in group_members]
        formatted_admins = [f"{admin}" for admin in admins]
        user_socket.sendall(f"[Members in {group_name} group: {', '.join(formatted_members)}]".encode('utf-8'))
        user_socket.sendall(f"[Admins in {group_name} group: {', '.join(formatted_admins)}]".encode('utf-8'))
    else:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        

# Function to authorize a member as an admin of a group
def authorize_group_member(message, user_socket, user_names, groups):
    parts = message.split()[2:]
    
    if len(parts) < 2:
        user_socket.sendall("[Invalid input. Please provide a group name and at least one username.]".encode('utf-8'))
        return

    group_name = parts[0]
    usernames_to_authorize = ' '.join(parts[1:]).split(',')

    if group_name not in groups:
        user_socket.sendall("[Group does not exist]".encode('utf-8'))
        return

    sender_username = user_names[user_socket]

    if sender_username not in groups[group_name]['admins']:
        user_socket.sendall("[You are not authorized to authorize members in this group]".encode('utf-8'))
        return

    for username_to_authorize in usernames_to_authorize:
        username_to_authorize = username_to_authorize.strip()

        if username_to_authorize not in user_names.values():
            user_socket.sendall(f"[{username_to_authorize} does not exist]".encode('utf-8'))
            continue

        # Check if the user to authorize is already an admin
        if username_to_authorize in groups[group_name]['admins']:
            user_socket.sendall(f"[{username_to_authorize} is already an admin in {group_name}]".encode('utf-8'))
            continue

        # Check if the user to authorize is not a member (and not already covered by being an admin)
        if username_to_authorize not in groups[group_name]['members']:
            user_socket.sendall(f"[{username_to_authorize} is not a member of the {group_name} group]".encode('utf-8'))
            continue

        # Authorize the user as an admin
        groups[group_name]['admins'].append(username_to_authorize)
        
        # Remove the user from regular members, if they are present
        if username_to_authorize in groups[group_name]['members']:
            groups[group_name]['members'].remove(username_to_authorize)

        # Inform the user who is assigned as admin
        for member_socket, member_username in user_names.items():
            if member_username == username_to_authorize:
                member_socket.sendall(f"[You have been assigned as an admin of the {group_name} group by {sender_username}]".encode('utf-8'))

        # Inform the admin who authorized the new member
        user_socket.sendall(f"[You have authorized {username_to_authorize} as an admin of the {group_name} group]".encode('utf-8'))

        # Send notification to other members and admins
        for member_socket, member_username in user_names.items():
            if member_username != sender_username and member_username != username_to_authorize and (member_username in groups[group_name]['members'] or member_username in groups[group_name]['admins']):
                member_socket.sendall(f"[{username_to_authorize} is authorized as an admin of the {group_name} group by {sender_username}]".encode('utf-8'))


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
