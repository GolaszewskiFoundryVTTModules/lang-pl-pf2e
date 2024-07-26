import os
import datetime
import logging
import shutil
import subprocess
import argparse
from localization_updater import LocalizationUpdater
from translator_config import log_directory, log_filename, temp_en_old_directory, core_en_directory, core_pl_directory, en_to_pl_file_pairs

def copy_files_and_directories(src_directory, dst_directory):
    if not os.path.exists(dst_directory):
        os.makedirs(dst_directory)
    for item in os.listdir(src_directory):
        src_path = os.path.join(src_directory, item)
        dst_path = os.path.join(dst_directory, item)
        if os.path.isdir(src_path):
            if os.path.exists(dst_path):
                copy_files_and_directories(src_path, dst_path)
            else:
                shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)

def run_js_script(script_path):
    try:
        result = subprocess.run(['node', script_path], check=True, text=True, capture_output=True)
        print(result.stdout)
        print(result.stderr)
    except subprocess.CalledProcessError as e:
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

    copy_files_and_directories(core_en_directory, temp_en_old_directory)

    if update_source_data:
        print("Running the pack extractor...")
        run_js_script("src/pack-extractor/pack-extractor.js")

    for en_old, en, pl in file_sets:
        updater = LocalizationUpdater(en_old, en, pl, verbose)
        updater.process(preform_regex_translate)
    
    shutil.rmtree(temp_en_old_directory)

if __name__ == "__main__":
    main()
