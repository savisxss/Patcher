import os
import asyncio
import argparse
import logging
from concurrent.futures import ProcessPoolExecutor
import hashlib
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("patch_generator.log"),
        logging.StreamHandler()
    ]
)

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, 'rb') as f:
        # Read in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

async def process_file(file_path, root_dir):
    """Process a single file and return its path and hash."""
    try:
        if os.path.isfile(file_path):
            relative_path = os.path.relpath(file_path, root_dir)
            file_hash = calculate_file_hash(file_path)
            logging.debug(f"Processed file: {relative_path}")
            return relative_path, file_hash
        return None
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        return None

async def generate_filelist(target_folder, exclusions=None, max_workers=None):
    """Generate a list of files with their hashes."""
    if not os.path.exists(target_folder):
        raise FileNotFoundError(f"Target folder does not exist: {target_folder}")
    
    if exclusions is None:
        exclusions = []
        
    # Add common exclusions
    exclusions.extend(['.git', '__pycache__', '.vscode', '.idea', '.DS_Store'])
    
    # Determine optimal number of workers
    max_workers = max_workers or min(32, os.cpu_count() + 4)
    
    filelist = []
    start_time = time.time()
    total_files = 0
    
    logging.info(f"Starting file list generation for: {target_folder}")
    logging.info(f"Using {max_workers} workers")
    
    # Use process pool for CPU-bound hashing operations
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        tasks = []
        
        # Walk directory tree
        for root, dirs, files in os.walk(target_folder):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclusions]
            
            for file in files:
                filepath = os.path.join(root, file)
                # Skip files in excluded directories
                skip = False
                for exclusion in exclusions:
                    if exclusion in filepath:
                        skip = True
                        break
                        
                if not skip:
                    total_files += 1
                    # Create task for each file
                    task = loop.run_in_executor(
                        executor, 
                        calculate_file_hash, 
                        filepath
                    )
                    tasks.append((filepath, task))
        
        # Process all files
        for filepath, task in tasks:
            try:
                file_hash = await task
                relative_path = os.path.relpath(filepath, target_folder)
                filelist.append(f"{relative_path},{file_hash}")
                
                # Log progress periodically
                if len(filelist) % 100 == 0:
                    logging.info(f"Processed {len(filelist)}/{total_files} files...")
                    
            except Exception as e:
                logging.error(f"Error processing {filepath}: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    logging.info(f"File list generation complete: {len(filelist)} files processed in {duration:.2f} seconds")
    return filelist

def save_filelist(filelist, output_file):
    """Save the file list to a file."""
    try:
        directory = os.path.dirname(output_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(output_file, 'w') as f:
            for file_entry in filelist:
                f.write(f"{file_entry}\n")
        logging.info(f'File list has been saved to {output_file}')
        return True
    except IOError as e:
        logging.error(f'Error saving file list to {output_file}: {e}')
        return False

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Generate a patch file list with checksums.')
    parser.add_argument('--target', '-t', dest='target_folder', required=True,
                      help='Target folder to generate file list from')
    parser.add_argument('--output', '-o', dest='output_file', default='patcher.txt',
                      help='Output file name (default: patcher.txt)')
    parser.add_argument('--exclude', '-e', dest='exclusions', action='append',
                      help='Directories or files to exclude (can be used multiple times)')
    parser.add_argument('--workers', '-w', dest='max_workers', type=int, default=None,
                      help='Maximum number of worker processes to use')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        logging.info(f"Target folder: {args.target_folder}")
        logging.info(f"Output file: {args.output_file}")
        if args.exclusions:
            logging.info(f"Exclusions: {', '.join(args.exclusions)}")
        
        filelist = await generate_filelist(
            args.target_folder, 
            exclusions=args.exclusions,
            max_workers=args.max_workers
        )
        
        if save_filelist(filelist, args.output_file):
            print(f"File list generated successfully: {len(filelist)} files")
        else:
            print("Error: Failed to save file list")
            return 1
            
    except Exception as e:
        logging.error(f'Error generating file list: {e}')
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)