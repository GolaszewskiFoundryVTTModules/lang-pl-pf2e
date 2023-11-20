import json
import csv
import os
from collections.abc import MutableMapping

def read_json_translation(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def find_first_json_file(directory):
    for file in os.listdir(directory):
        if file.endswith('.json'):
            return os.path.join(directory, file)
    return None  # Return None if no JSON file is found

def write_to_csv(file_path, english_dict, polish_dict):
    with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)  # Quote all fields
        if os.stat(file_path).st_size == 0:  # File is empty, write headers
            writer.writerow(["Localization Key", "English", "Polish"])
        for key in english_dict:
            if key in polish_dict:  # If the key exists in Polish translations
                writer.writerow([key, english_dict[key], polish_dict[key]])

def main():
    # Find the first JSON file in 'en' and 'pl' directories
    english_file_path = find_first_json_file('en')
    polish_file_path = find_first_json_file('pl')

    # Check if JSON files were found in both directories
    if not english_file_path or not polish_file_path:
        print("One or both directories do not contain a JSON file.")
        return

    # Read and flatten the JSON translation files
    english_translations = flatten_dict(read_json_translation(english_file_path))
    polish_translations = flatten_dict(read_json_translation(polish_file_path))

    # Write translations to CSV
    csv_file_path = 'TranslationReference.csv'
    write_to_csv(csv_file_path, english_translations, polish_translations)

    print("Translations have been written to", csv_file_path)

if __name__ == "__main__":
    main()
