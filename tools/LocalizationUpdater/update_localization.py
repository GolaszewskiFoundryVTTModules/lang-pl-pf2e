import os
import datetime
import logging
import shutil
import subprocess
import argparse
import json
from localization_updater import LocalizationUpdater
from translator_config import log_directory, log_filename, temp_en_old_directory, core_en_directory, core_pl_directory, en_to_pl_file_pairs

def _copy_files_and_directories(src_directory, dst_directory):
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
                _copy_files_and_directories(src_path, dst_path)
            else:
                # If the subdirectory does not exist at the destination, copy it
                shutil.copytree(src_path, dst_path)
        else:
            # Copy files and overwrite if necessary
            shutil.copy2(src_path, dst_path)

def _run_js_script(script_path):
    try:
        # Run the .js script with Node.js
        result = subprocess.run(['node', script_path], check=True, text=True, capture_output=True)
        # Output the result (stdout and stderr)
        print(result.stdout)
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        # Handle errors in the called .js script
        print(f"An error occurred while running {script_path}: {e}")

def _check_config_consistency():
    """Compare pack-extractor-config.json with translator_config.py for any discrepancies"""
    
    # Read pack-extractor config
    with open("src/pack-extractor/pack-extractor-config.json", 'r') as f:
        extractor_config = json.load(f)
    
    # Get all configured packs from extractor config, excluding _folders and _packs-folders
    extractor_packs = {
        pack for group in extractor_config["packs"].values()
        for pack in group["packNames"]
        if not (pack.endswith('_folders') or pack.endswith('_packs-folders'))
    }
    
    # Get configured packs from translator config, preserving full paths
    translator_packs = {
        pair[0].split('/')[-1]: pair[0] 
        for pair in en_to_pl_file_pairs 
        if pair[0].startswith('compendium/') 
        and not (pair[0].endswith('_folders') or pair[0].endswith('_packs-folders'))
    }
    
    # Find discrepancies
    missing_in_translator = extractor_packs - set(translator_packs.keys())
    missing_in_extractor = set(translator_packs.keys()) - extractor_packs
    
    if missing_in_translator or missing_in_extractor:
        print("\n\033[33mWarning: Configuration discrepancies found:\033[0m")
        
        if missing_in_translator:
            print("\n\033[33mFiles configured in pack-extractor but missing in translator_config.py:\033[0m")
            for pack in sorted(missing_in_translator):
                print(f"\033[33m- Add: (\"compendium/{pack}\", \"compendium/pf2e.{pack}\")\033[0m")
        
        if missing_in_extractor:
            print("\n\033[33mFiles configured in translator_config.py but missing in pack-extractor-config.json:\033[0m")
            for pack in sorted(missing_in_extractor):
                full_path = translator_packs[pack]
                print(f"\033[33m- Add \"{pack}\" to appropriate pack group (from {full_path})\033[0m")

def main():
    os.makedirs(log_directory, exist_ok=True)
    logging.basicConfig(level=logging.INFO, filename=log_filename, filemode='w', format='%(message)s')

    parser = argparse.ArgumentParser(description='Run the script with optional update source data flag.')
    parser.add_argument('--UpdateSourceData', action='store_true', help='Update source data if set to true.')
    parser.add_argument('--PerformRegexTranslate', action='store_true', help='Forces re-processing all strings by regex translations.')
    parser.add_argument('-v', '--Verbose', action='store_true', help='Enable verbose logging.')
    args = parser.parse_args()

    update_source_data = args.UpdateSourceData
    perform_regex_translate = args.PerformRegexTranslate
    verbose = args.Verbose

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
    _copy_files_and_directories(core_en_directory, temp_en_old_directory)

    if update_source_data:
        # update the source files
        print("Running the pack extractor...")
        _run_js_script("src/pack-extractor/pack-extractor.js")
        
    # Check config consistency
    print("\nChecking configuration consistency...")
    _check_config_consistency()

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
        updater.process(perform_regex_translate)
    
    shutil.rmtree(temp_en_old_directory)

if __name__ == "__main__":
    main()
