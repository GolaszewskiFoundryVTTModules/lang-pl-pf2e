import os
import json
import logging
from tqdm import tqdm
from collections import Counter
import datetime

# Create "Logs" directory if it doesn't exist
log_directory = "Logs"
os.makedirs(log_directory, exist_ok=True)

# Current date and time for the log filename
current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = os.path.join(log_directory, f"LocalizationUpdate_{current_time}.log")

# Setup logging configuration
logging.basicConfig(level=logging.INFO, 
                    filename=log_filename, 
                    filemode='w', 
                    format='%(levelname)s: %(message)s')

# Setup logging configuration
logging.basicConfig(level=logging.INFO)

# Global counters
changed_keys_count = 0
new_keys_count = 0
removed_keys_count = 0
outdated_records_count = 0

# Additional global variables to track keys
renamed_keys = []
outdated_keys = []
new_keys = []
removed_keys = []

# Global container declarations
en_old_extracted = {}
en_extracted = {}
pl_extracted = {}

def get_file_from_directory(directory):
    try:
        os.makedirs(directory, exist_ok=True)
        files = [f for f in os.listdir(directory) if f.endswith('.json')]
        
        if len(files) == 0:
            logging.error(f"No JSON file found in {directory} directory.")
            return None
        elif len(files) > 1:
            logging.warning(f"Multiple JSON files found in {directory} directory. Choosing the first one: {files[0]}")
        
        filepath = os.path.join(directory, files[0])
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"An error occurred while loading the JSON file from {directory} directory: {str(e)}")
        return None

def extract_localization_dict(obj, current_path='', result_dict=None):
    if obj is None:
        return None
    
    if result_dict is None:
        result_dict = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            # Construct the new path by concatenating the current key
            new_path = f'{current_path}.{key}' if current_path else key
            extract_localization_dict(value, new_path, result_dict)
    else:
        # Store the string at the current path
        result_dict[current_path] = str(obj)

    return result_dict

def update_localization():
    global en_old_extracted, en_extracted, pl_extracted
    global changed_keys_count, new_keys_count, removed_keys_count, outdated_records_count
    global renamed_keys, outdated_keys, new_keys, removed_keys

    # Create reverse lookup dictionaries for old and new values
    old_value_to_key = {v: k for k, v in en_old_extracted.items()}
    new_value_to_key = {v: k for k, v in en_extracted.items()}

    # Count occurrences of each value
    old_value_counts = Counter(en_old_extracted.values())
    new_value_counts = Counter(en_extracted.values())

    for new_key, new_value in tqdm(en_extracted.items(), desc="Processing new keys"):
        old_key = old_value_to_key.get(new_value)

        # value's key got renamed
        if old_key and old_key != new_key and old_value_counts[new_value] == 1 and new_value_counts[new_value] == 1:
            changed_keys_count += 1
            pl_extracted[new_key] = pl_extracted.pop(old_key, None)
            renamed_keys.append((old_key, new_key))

        # key's value changed
        elif new_value != en_old_extracted.get(new_key, None) and new_key in pl_extracted:
            outdated_records_count += 1
            pl_extracted[new_key] += " (OUTDATED!)"
            outdated_keys.append(new_key)

        # new key
        elif new_key not in pl_extracted:
            new_keys_count += 1
            pl_extracted[new_key] = ""
            new_keys.append(new_key)

    # Delete old keys
    for old_key in tqdm(list(en_old_extracted.keys()), desc="Deleting obsolete keys", leave=False):
        if old_key not in en_extracted:
            removed_keys_count += 1
            pl_extracted.pop(old_key, None)
            removed_keys.append(old_key)


def validate_keys_match(path=''):
    errors = []

    # Check all keys in the reference dictionary to see if they exist in the target
    for key in en_extracted.keys():
        current_path = f"{path}.{key}" if path else key
        if key not in pl_extracted:
            errors.append(f"Missing key in target: {current_path}")
        else:
            if isinstance(en_extracted[key], dict) and isinstance(pl_extracted[key], dict):
                errors.extend(validate_keys_match(en_extracted[key], pl_extracted[key], current_path))
            elif isinstance(en_extracted[key], dict) and not isinstance(target_dict[key], dict):
                errors.append(f"Mismatched types at {current_path}, expected a dict in target but found a non-dict.")
            elif not isinstance(en_extracted[key], dict) and isinstance(pl_extracted[key], dict):
                errors.append(f"Mismatched types at {current_path}, expected a non-dict in target but found a dict.")

    # Check all keys in the target dictionary to see if they have become obsolete
    for key in pl_extracted.keys():
        current_path = f"{path}.{key}" if path else key
        if key not in en_extracted:
            errors.append(f"Obsolete key in target: {current_path}")

    return errors

def rebuild_nested_json(flat_dict):
    nested_json = {}

    for compound_key, value in flat_dict.items():
        keys = compound_key.split('.')
        current_level = nested_json

        for key in keys[:-1]:
            # Create a new dictionary at the current level if the key doesn't exist
            if key not in current_level:
                current_level[key] = {}
            current_level = current_level[key]

        # Set the value at the final key
        current_level[keys[-1]] = value

    return nested_json

def save_file_to_directory(directory, data):
    try:
        os.makedirs(directory, exist_ok=True)
        files = [f for f in os.listdir(directory) if f.endswith('.json')]
        filename = files[0] if files else 'data.json'
        filepath = os.path.join(directory, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"An error occurred while saving the JSON file to {directory} directory: {str(e)}")

def main():
    global en_old_extracted, en_extracted, pl_extracted
    global changed_keys_count, new_keys_count, removed_keys_count, outdated_records_count

    en_old_extracted = extract_localization_dict(get_file_from_directory('en-old'))
    en_extracted = extract_localization_dict(get_file_from_directory('en'))
    pl_extracted = extract_localization_dict(get_file_from_directory('pl'))

    if en_old_extracted is None or en_extracted is None or pl_extracted is None:
        logging.error("Unable to proceed due to missing data.")
        return

    update_localization()    

    # Log the results
    logging.info("Update Complete")
    logging.info(f"Number of renamed keys (transfered): {changed_keys_count}")
    for old_key, new_key in renamed_keys:
        logging.info(f"  {old_key} -> {new_key}")

    logging.info(f"Number of outdated records: {outdated_records_count}")
    for key in outdated_keys:
        logging.info(f"  {key}")

    logging.info(f"Number of new keys added: {new_keys_count}")
    for key in new_keys:
        logging.info(f"  {key}")

    logging.info(f"Number of obsolete keys deleted: {removed_keys_count}")
    for key in removed_keys:
        logging.info(f"  {key}")
        
    # Validate that PL data has all and only the keys present in EN data
    validation_errors = validate_keys_match()
    if validation_errors:
        for error in validation_errors:
            logging.error(error)
        logging.error("Validation failed, the keys in English and Polish files do not match.")
    else:
        logging.info("Validation successful, all keys match.")

    save_file_to_directory('pl', rebuild_nested_json(pl_extracted))

if __name__ == "__main__":
    main()