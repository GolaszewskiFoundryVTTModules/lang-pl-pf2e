import os
import json
import logging

# Setup logging configuration
logging.basicConfig(level=logging.INFO)

def get_json_files_from_directory(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    json_file_paths = [os.path.join(directory, file) for file in json_files]
    return json_file_paths

def validate_keys_match(ref_dict, target_dict, ref_path='', target_path=''):
    errors = []

    for key, value in ref_dict.items():
        current_path = f"{ref_path}.{key}" if ref_path else key

        if key not in target_dict:
            errors.append(f"Missing key in target: {current_path}")
        elif isinstance(value, dict) and isinstance(target_dict[key], dict):
            # Recursive validation for nested dictionaries
            errors.extend(validate_keys_match(value, target_dict[key], current_path, current_path))
        elif isinstance(value, dict) and not isinstance(target_dict[key], dict):
            errors.append(f"Mismatched structure at {current_path}: Expected dict in target, found {type(target_dict[key]).__name__}")

    for key in target_dict:
        if key not in ref_dict:
            current_path = f"{target_path}.{key}" if target_path else key
            errors.append(f"Obsolete key in target: {current_path}")

    return errors

def load_and_validate(directory_ref, directory_target):
    ref_files = get_json_files_from_directory(directory_ref)
    target_files = get_json_files_from_directory(directory_target)

    if not ref_files or not target_files:
        logging.error("No JSON files found for comparison.")
        return

    for ref_file, target_file in zip(ref_files, target_files):  # This assumes both directories have the same number of files and order
        logging.info(f"Validating {ref_file} against {target_file}")
        ref_data = load_json_file(ref_file)
        target_data = load_json_file(target_file)

        if ref_data and target_data:
            errors = validate_keys_match(ref_data, target_data)
            if errors:
                for error in errors:
                    logging.error(error)
                logging.error(f"Validation failed for {ref_file} against {target_file} with the above errors.")
            else:
                logging.info(f"Validation successful for {ref_file} against {target_file} - No discrepancies found.")

def load_json_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load JSON file {filepath}: {str(e)}")
        return None

def main():
    directory_en = 'en'  # Replace with your actual English JSON directory
    directory_pl = 'pl'  # Replace with your actual Polish JSON directory

    load_and_validate(directory_en, directory_pl)

if __name__ == "__main__":
    main()
