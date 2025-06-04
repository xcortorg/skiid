import os
import sys

import requests


def download_lavalink():
    # URL of the Lavalink.jar file
    url = (
        "https://github.com/lavalink-devs/Lavalink/releases/download/4.0.8/Lavalink.jar"
    )

    # Name of the file to save
    filename = "Lavalink.jar"

    try:
        # Send GET request to download the file
        print(f"Attempting to download from: {url}")

        # Add headers to mimic a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        response = requests.get(url, headers=headers, stream=True)

        # Raise an exception if the request was unsuccessful
        response.raise_for_status()

        # Get the total file size
        total_size = int(response.headers.get("content-length", 0))

        print(f"File size: {total_size/1024/1024:.2f} MB")

        # Open the file in write binary mode
        with open(filename, "wb") as file:
            if total_size == 0:
                print(
                    "Warning: Content length is 0. File might be empty or the server didn't report the size."
                )
                file.write(response.content)
            else:
                # Download the file in chunks and show progress
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        # Show download progress
                        progress = int(50 * downloaded / total_size)
                        sys.stdout.write(
                            f"\rDownloading: [{'='*progress}{' '*(50-progress)}] {downloaded/total_size*100:.1f}%"
                        )
                        sys.stdout.flush()
                print("\nDownload completed!")

        # Verify the file exists and has content
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"File saved as {filename}")
            print(f"File size on disk: {file_size/1024/1024:.2f} MB")
            if file_size == 0:
                print("Warning: The downloaded file is empty!")
        else:
            print("Error: File was not saved correctly!")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    download_lavalink()
