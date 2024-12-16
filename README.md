# SocketProgramming-Chatbot

This project is a simple chat application using socket programming in Python. It includes both a client and a server component, allowing multiple users to connect to a server, send messages, and create or manage groups.

## Features

- **Real-time messaging**: Users can send and receive messages in real-time.
- **Group chat**: Users can create, join, and manage groups.
- **Private messaging**: Users can send private messages to other users.
- **Commands**: Various commands to manage groups and users, such as `@quit`, `@names`, `@group set`, `@group send`, etc.

## Getting Started

### Prerequisites

- Python 3.x

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/SocketProgramming-Chatbot.git
    cd SocketProgramming-Chatbot
    ```

2. Run the server:
    ```sh
    python server.py
    ```

3. Run the client:
    ```sh
    python client.py
    ```

## Usage

### Server Commands

- `@quit`: Shut down the server.

### Client Commands

- `@quit`: Disconnect from the server.
- `@names`: Get a list of connected users.
- `@group set <group_name> <members>`: Create a new group.
- `@group send <group_name> <message>`: Send a message to a group.
- `@group delete <group_name>`: Delete a group.
- `@group leave <group_name>`: Leave a group.
- `@group add <group_name> <members>`: Add members to a group.
- `@group list`: List all groups the user is in.
- `@group remove <group_name> <members>`: Remove members from a group.
- `@group members <group_name>`: List all members in a group.
- `@group authorize <group_name> <members>`: Authorize members as admins of a group.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.
