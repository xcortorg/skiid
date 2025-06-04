import os
from concurrent.futures import ThreadPoolExecutor


def write_chunk(file_name, start, end):
    """
    Writes a chunk of data to the file.

    Parameters:
    file_name (str): The name of the file to be written.
    start (int): The starting position of the chunk.
    end (int): The ending position of the chunk.
    """
    with open(file_name, "r+b") as f:
        f.seek(start)
        f.write(b"A" * (end - start))


def generate_large_text_file(file_name, size_in_gb, num_threads=8):
    """
    Generates a large text file with the specified size in GB using multi-threading.

    Parameters:
    file_name (str): The name of the file to be created.
    size_in_gb (int): The size of the file to be created in gigabytes.
    num_threads (int): The number of threads to use for writing.
    """
    chunk_size = 1024 * 1024 * 1024  # 1 GB
    total_size = size_in_gb * 1024 * 1024 * 1024  # Size in bytes

    # Create an empty file with the desired size
    with open(file_name, "wb") as f:
        f.write(b"\0" * total_size)

    # Determine the size of each chunk to be written
    num_chunks = (total_size + chunk_size - 1) // chunk_size
    chunks = [
        (i * chunk_size, min((i + 1) * chunk_size, total_size))
        for i in range(num_chunks)
    ]

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit write tasks to the thread pool
        futures = [
            executor.submit(write_chunk, file_name, start, end) for start, end in chunks
        ]
        # Wait for all futures to complete
        for future in futures:
            future.result()


if __name__ == "__main__":
    file_name = "large_file.txt"
    size_in_gb = 100
    generate_large_text_file(file_name, size_in_gb)
