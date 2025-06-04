#!/bin/bash

# Discord API Token
DISCORD_API_TOKEN="MTI4NDAzNzAyNjY3MjI3OTYzNQ.GwlTsP.08319iFsnsHJVLHz-NKC7F7Z_Ysl7ErJSqipe8"

# Function to get username from UID (using Discord API)
get_username_from_uid() {
    uid=$1
    response=$(curl -s -X GET "https://discord.com/api/v10/users/$uid" -H "Authorization: Bot $DISCORD_API_TOKEN")
    
    # Extracting the username from the API response
    username=$(echo $response | jq -r '.username')

    if [[ "$username" == "null" ]]; then
        echo "Error: UID not found or invalid."
    else
        echo "Username for UID $uid: $username"
    fi
}

# Function to convert UID to Base64
uid_to_base64() {
    uid=$1
    base64=$(echo -n $uid | base64)
    echo "Base64 encoding for UID $uid: $base64"
}

# Function to display menu and handle user input
show_menu() {
    echo "Choose an option:"
    echo "[1] UID to Username"
    echo "[2] Username to UID (placeholder)"
    echo "[3] UID to Base64"
    echo "[q] Quit"
    read -p "Enter your choice (1, 2, 3, or q): " choice

    case $choice in
        1)
            read -p "Enter Discord UID: " uid
            get_username_from_uid $uid
            ;;
        2)
            echo "Username to UID is not directly supported without bot interaction."
            ;;
        3)
            read -p "Enter Discord UID: " uid
            uid_to_base64 $uid
            ;;
        q)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            ;;
    esac
}

# Main loop
while true; do
    show_menu
done
