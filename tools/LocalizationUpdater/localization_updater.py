import os
import json
import logging
import regex
from collections import Counter
from tqdm import tqdm
import datetime
from difflib import SequenceMatcher

from auto_translation_regex import replacement_patterns

class LocalizationUpdater:
    
    def __init__(self, en_old_path, en_path, pl_path, verbose):
        self.en_old_path = en_old_path
        self.en_path = en_path
        self.pl_path = pl_path
        self.verbose = verbose

        self.en_old_extracted = {}
        self.en_extracted = {}
        self.pl_extracted = {}

        self.new_keys = []
        self.removed_keys = []
        self.renamed_keys = []
        self.outdated_keys = []
        self.updated_eng_keys = []
        self.rudimentary_translations_updated = []

        self.replacement_patterns = replacement_patterns

    def get_file_from_directory(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"An error occurred while loading the JSON file: {filepath}: {str(e)}")
            return None

    def save_file_to_directory(self, filepath, data):
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"An error occurred while saving the JSON file to {filepath}: {str(e)}")

    def extract_localization_dict(self, obj, current_path='', result_dict=None):
        if obj is None:
            return None
        if result_dict is None:
            result_dict = {}
        if isinstance(obj, dict):
            for key, value in obj.items():
                if current_path:
                    if current_path[-1] == "." and key[0]==" " or key[0]==".":
                        new_path = f'{current_path}{key}'
                    else:
                        new_path = f'{current_path}.{key}'
                else:
                    new_path = key
                self.extract_localization_dict(value, new_path, result_dict)
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                new_path = f"{current_path}{{{index}}}"
                self.extract_localization_dict(item, new_path, result_dict)
        else:
            result_dict[current_path] = obj
        return result_dict

    def rebuild_nested_json(self, flat_dict):
        nested_json = {}
        for compound_key, value in flat_dict.items():
            keys = [k for k in regex.split(r'\.(?![\s.])', compound_key) if k]
            current_level = nested_json
            for i, key in enumerate(keys):
                if '{' in key and '}' in key:
                    list_name, list_index = key.replace('}', '').split('{')
                    list_index = int(list_index)
                    if list_name not in current_level:
                        current_level[list_name] = []
                    while len(current_level[list_name]) <= list_index:
                        current_level[list_name].append(None)
                    if i == len(keys) - 1:
                        current_level[list_name][list_index] = value
                    else:
                        if current_level[list_name][list_index] is None:
                            current_level[list_name][list_index] = {}
                        current_level = current_level[list_name][list_index]
                else:
                    if i == len(keys) - 1:
                        current_level[key] = value
                    else:
                        if key not in current_level:
                            current_level[key] = {}
                        current_level = current_level[key]
        return nested_json

    def generate_concise_diff(self, old_value, new_value):
        s = SequenceMatcher(None, old_value, new_value)
        diff = []
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == 'replace':
                diff.append('\n')
                diff.append('      - ' + old_value[i1:i2].replace("\n", "\\n"))
                diff.append('      + ' + new_value[j1:j2].replace("\n", "\\n"))
            elif tag == 'delete':
                diff.append('\n')
                diff.append('      - ' + old_value[i1:i2].replace("\n", "\\n"))
            elif tag == 'insert':
                diff.append('\n')
                diff.append('      + ' + new_value[j1:j2].replace("\n", "\\n"))
        return ''.join(diff)

    def is_translation_rudimentary(self, en_str, pl_str, verbose = False):
        if not en_str or not pl_str:
            print("Attempted to compare null string(s)")
            return False
        
        regex_patterns = [
             r'@[^\]]+\[([^\[]|\[\S+\])+\]',
             r'(?<!\])\{[^\{]+\}',
             r'(?<!\[)\[[^\[\]]+\]', 
             r'\[\[[^(\]\])]+\]\]', 
             r'<[^<]+>',
             r'\\n'
        ]

        def clean_string(s, patterns):
            for pattern in patterns:
                s = regex.sub(pattern, '', s)
            return s

        en_str_cleaned = clean_string(en_str, regex_patterns)
        pl_str_cleaned = clean_string(pl_str, regex_patterns)

        if(verbose):
            print(en_str_cleaned)
            print(pl_str_cleaned)
            matcher = SequenceMatcher(None, en_str_cleaned, pl_str_cleaned)
            print(matcher.ratio())

        similarity_threshold = 0.75
        matcher = SequenceMatcher(None, en_str_cleaned, pl_str_cleaned)
        similarity = matcher.ratio()
        return similarity >= similarity_threshold

    def auto_pretranslate(self, en_str):
        def save_and_replace_brackets(text):
            bracketed_texts = []
            open_brackets = []
            placeholders = []
            def generate_placeholder(index):
                return f"__PLACEHOLDER_{index}__"
            i = 0
            while i < len(text):
                if text[i] == '[':
                    open_brackets.append(i)
                elif text[i] == ']' and open_brackets:
                    start = open_brackets.pop()
                    if open_brackets:
                        continue
                    encapsulated = text[start:i+1]
                    bracketed_texts.append(encapsulated)
                    placeholder = generate_placeholder(len(bracketed_texts) - 1)
                    placeholders.append((start, i, placeholder))
                i += 1
            for start, end, placeholder in reversed(placeholders):
                text = text[:start] + placeholder + text[end+1:]
            return text, bracketed_texts

        def restore_bracketed_text(modified_text, bracketed_texts):
            for i, original_text in enumerate(bracketed_texts):
                modified_text = modified_text.replace(f"__PLACEHOLDER_{i}__", original_text)
            return modified_text
        
        def replace_with_patterns(text, replacements):
            for pattern, replacement in replacements:
                text = regex.sub(pattern, replacement, text)
            return text

        if en_str == None:
            print("Cannot pretranslate empty string")
            return en_str

        text_with_placeholders, bracketed_texts = save_and_replace_brackets(en_str)
        modified_text = replace_with_patterns(text_with_placeholders, self.replacement_patterns)
        final_text = restore_bracketed_text(modified_text, bracketed_texts)
        return final_text
    
    def update_localization(self):
        old_value_counts = Counter(self.en_old_extracted.values())
        new_value_counts = Counter(self.en_extracted.values())
        unique_old_values = {value for value, count in old_value_counts.items() if count == 1}
        unique_new_values = {value for value, count in new_value_counts.items() if count == 1}
        old_value_to_key = {value: key for key, value in self.en_old_extracted.items() if value in unique_old_values}
        new_value_to_key = {value: key for key, value in self.en_extracted.items() if value in unique_new_values}

        for new_key, new_value in tqdm(self.en_extracted.items(), desc=f"Processing {os.path.basename(self.pl_path)}"):
            if new_key in self.pl_extracted and self.pl_extracted.get(new_key) == new_value:
                continue
            old_key = old_value_to_key.get(new_value, None)
            if old_key and old_key != new_key and new_value in unique_new_values:
                if old_key not in self.pl_extracted:
                    print(f"Did not find old key {old_key} in polish {os.path.basename(self.pl_path)}. It may have been updated already")
                else:
                    self.pl_extracted[new_key] = self.pl_extracted.get(old_key, None)
                    self.renamed_keys.append((old_key, new_key))
            elif (new_key in self.pl_extracted and new_value != self.en_old_extracted.get(new_key, None)):
                if self.pl_extracted.get(new_key) == self.en_old_extracted.get(new_key):
                    self.pl_extracted[new_key] = self.auto_pretranslate(new_value)
                    self.updated_eng_keys.append(new_key)
                elif self.is_translation_rudimentary(self.auto_pretranslate(self.en_old_extracted.get(new_key, None)), self.pl_extracted.get(new_key)):
                    self.pl_extracted[new_key] = self.auto_pretranslate(new_value)
                    self.rudimentary_translations_updated.append(new_key)
                else:
                    old_value = self.en_old_extracted.get(new_key, "")
                    diff_string = self.generate_concise_diff(old_value, new_value)
                    self.outdated_keys.append((new_key, diff_string))
            elif new_key not in self.pl_extracted:
                self.pl_extracted[new_key] = self.auto_pretranslate(new_value)
                self.new_keys.append(new_key)
        for old_key in tqdm(list(self.en_old_extracted.keys()), desc=f"Deleting obsolete keys in {os.path.basename(self.pl_path)}", leave=False):
            if old_key not in self.en_extracted:
                self.pl_extracted.pop(old_key, None)
                self.removed_keys.append(old_key)

    def validate_keys_match(self, path=''):
        errors = []
        for key in self.en_extracted.keys():
            current_path = f"{path}.{key}" if path else key
            if key not in self.pl_extracted:
                errors.append(f"Missing key in target: {current_path}")
            else:
                if isinstance(self.en_extracted[key], dict) and isinstance(self.pl_extracted[key], dict):
                    errors.extend(self.validate_keys_match(self.en_extracted[key], self.pl_extracted[key], current_path))
                elif isinstance(self.en_extracted[key], dict) and not isinstance(self.pl_extracted[key], dict):
                    errors.append(f"Mismatched types at {current_path}, expected a dict in target but found a non-dict.")
                elif not isinstance(self.en_extracted[key], dict) and isinstance(self.pl_extracted[key], dict):
                    errors.append(f"Mismatched types at {current_path}, expected a non-dict in target but found a dict.")
        for key in self.pl_extracted.keys():
            current_path = f"{path}.{key}" if path else key
            if key not in self.en_extracted:
                errors.append(f"Obsolete key in target: {current_path}")
        return errors

    def process(self, perform_regex_translate):
        self.en_old_extracted = self.extract_localization_dict(self.get_file_from_directory(self.en_old_path))
        self.en_extracted = self.extract_localization_dict(self.get_file_from_directory(self.en_path))
        self.pl_extracted = self.extract_localization_dict(self.get_file_from_directory(self.pl_path))

        if self.en_old_extracted is None or self.en_extracted is None or self.pl_extracted is None:
            logging.info(f"{os.path.basename(self.pl_path)}:")
            logging.error("Unable to proceed due to missing data.")
            return

        if not perform_regex_translate:
            if self.pl_extracted == self.en_extracted:
                return
            self.update_localization()
        else:
            for key, value in tqdm(self.pl_extracted.items(), desc=f"Regex-translating {os.path.basename(self.pl_path)}"):
                self.pl_extracted[key] = self.auto_pretranslate(self.pl_extracted[key])

        if not any([self.new_keys, self.removed_keys, self.renamed_keys, self.updated_eng_keys, self.outdated_keys]) and not perform_regex_translate:
            return

        if self.verbose or any([self.outdated_keys]):
            logging.info(f"{os.path.basename(self.pl_path)}:")
            if self.new_keys and self.verbose:
                logging.info(f"  Added keys: {len(self.new_keys)}")
                for key in self.new_keys:
                    logging.info(f"    {key}")
            if self.removed_keys and self.verbose:
                logging.info(f"  Deleted keys: {len(self.removed_keys)}")
                for key in self.removed_keys:
                    logging.info(f"    {key}")
            if self.renamed_keys and self.verbose:
                logging.info(f"  Renamed keys (transferred): {len(self.renamed_keys)}")
                for old_key, new_key in self.renamed_keys:
                    logging.info(f"    {old_key} -> {new_key}")
            if self.updated_eng_keys and self.verbose:
                logging.info(f"  Updated english keys: {len(self.updated_eng_keys)}")
                for key in self.updated_eng_keys:
                    logging.info(f"    {key}")
            if self.rudimentary_translations_updated and self.verbose:
                logging.info(f"  Rudimentary translations updated: {len(self.rudimentary_translations_updated)}")
                for key in self.rudimentary_translations_updated:
                    logging.info(f"    {key}")
            if self.outdated_keys:
                logging.info(f"  Outdated records: {len(self.outdated_keys)}")
                for key, diff in self.outdated_keys:
                    logging.info(f"    Key: {key}\n    Diff:{diff}\n")
            validation_errors = self.validate_keys_match()
            if validation_errors:
                for error in validation_errors:
                    logging.error(error)
                logging.error("Validation failed, the keys in English and Polish files do not match.")
            else:
                logging.info("Validation successful, all keys match.")
        ordered_pl = {}
        for key in self.en_extracted.keys():
            ordered_pl[key] = self.pl_extracted.get(key, None)
        self.pl_extracted = ordered_pl
        logging.info("\n")
        self.save_file_to_directory(self.pl_path, self.rebuild_nested_json(self.pl_extracted))
