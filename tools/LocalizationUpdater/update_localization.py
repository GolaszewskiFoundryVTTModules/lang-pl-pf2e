import os
import datetime
import logging
import shutil
import subprocess
import argparse
from localization_updater import LocalizationUpdater
from translator_config import log_directory, log_filename, temp_en_old_directory, core_en_directory, core_pl_directory, en_to_pl_file_pairs

def copy_files_and_directories(src_directory, dst_directory):
    """
    Recursively copy all files and directories from the source directory 
    to the destination directory. Existing files in the destination directory 
    with the same name will be overwritten.
    """
    if not os.path.exists(dst_directory):
        os.makedirs(dst_directory)
    for item in os.listdir(src_directory):
        src_path = os.path.join(src_directory, item)
        dst_path = os.path.join(dst_directory, item)
        if os.path.isdir(src_path):
            # Recursively copy the entire subdirectory
            if os.path.exists(dst_path):
                # If the subdirectory exists at the destination, recursively copy its contents
                copy_files_and_directories(src_path, dst_path)
            else:
                # If the subdirectory does not exist at the destination, copy it
                shutil.copytree(src_path, dst_path)
        else:
            # Copy files and overwrite if necessary
            shutil.copy2(src_path, dst_path)

def run_js_script(script_path):
    try:
        # Run the .js script with Node.js
        result = subprocess.run(['node', script_path], check=True, text=True, capture_output=True)
        # Output the result (stdout and stderr)
        print(result.stdout)
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        # Handle errors in the called .js script
        print(f"An error occurred while running {script_path}: {e}")

def main():
    os.makedirs(log_directory, exist_ok=True)
    logging.basicConfig(level=logging.INFO, filename=log_filename, filemode='w', format='%(message)s')

    parser = argparse.ArgumentParser(description='Run the script with optional update source data flag.')
    parser.add_argument('--UpdateSourceData', action='store_true', help='Update source data if set to true.')
    parser.add_argument('--PreformRegexTranslate', action='store_true', help='Forces re-processing all strings by regex translations.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging.')
    args = parser.parse_args()

    update_source_data = args.UpdateSourceData
    preform_regex_translate = args.PreformRegexTranslate
    verbose = args.verbose

    file_sets = []
    for en_name, pl_name in en_to_pl_file_pairs:
        file_sets.append(
            (
                temp_en_old_directory + en_name + ".json",
                core_en_directory + en_name + ".json",
                core_pl_directory + pl_name + ".json"
            )
        )

    # back up the old localization source
    copy_files_and_directories(core_en_directory, temp_en_old_directory)

    if update_source_data:
        # update the source files
        print("Running the pack extractor...")
        run_js_script("src/pack-extractor/pack-extractor.js")

    for en_old, en, pl in file_sets:
        # Check if the Polish file exists
        if not os.path.exists(pl):
            if verbose:
                print(f"File at {pl} does not exist. Creating a copy from {en}.")
            # Copy the English file to the Polish path
            shutil.copy(en, pl)
            if verbose:
                print(f"File copied from {en} to {pl}.")

        updater = LocalizationUpdater(en_old, en, pl, verbose)
        updater.process(preform_regex_translate)
    
    shutil.rmtree(temp_en_old_directory)

if __name__ == "__main__":
    main()
