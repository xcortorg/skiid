import os

def split_sql_file(input_file, max_size_mb=91):
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
    file_count = 0
    current_file_size = 0
    current_file = None

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if current_file is None or current_file_size >= max_size_bytes:
                if current_file is not None:
                    current_file.close()
                file_count += 1
                current_file = open(f'migration_{file_count}.sql', 'w', encoding='utf-8')
                current_file_size = 0

            current_file.write(line)
            current_file_size += len(line.encode('utf-8'))  # Get the size of the line in bytes

        if current_file is not None:
            current_file.close()

    print(f'Split into {file_count} files.')

# Example usage
split_sql_file('output_file.sql')