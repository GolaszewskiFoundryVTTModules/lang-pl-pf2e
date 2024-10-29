import os
import json
import logging
import regex
from collections import Counter
from tqdm import tqdm
import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple, Optional

from auto_translation_regex import replacement_patterns

class LocalizationUpdater:
    # Reference symbols detection regex patterns
    RUDIMENTARY_TRANSLATION_REGEX_PATTERNS = [
        r'@[^\]]+\[([^\[]|\[\S+\])+\]',
        r'(?<!\])\{[^\{]+\}',
        r'(?<!\[)\[[^\[\]]+\]', # single square, to remove damage
        r'\[\[[^(\]\])]+\]\]',  # afterwards, double square, to remove formulas
        r'<[^<]+>',
        r'\\n'
    ]

    def __init__(self, en_old_path: str, en_path: str, pl_path: str, verbose: bool):
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

        # Pre-compile all auto-translation regex patterns
        self.compiled_replacement_patterns = [
            (regex.compile(pattern), replacement)
            for pattern, replacement in replacement_patterns
        ]

        self.compiled_patterns = [regex.compile(pattern) for pattern in self.RUDIMENTARY_TRANSLATION_REGEX_PATTERNS]

    def _get_file_from_directory(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"An error occurred while loading the JSON file: {filepath}: {str(e)}")
            return None

    def _save_file_to_directory(self, filepath, data):
        try:
            # Ensure the directory of the file exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the data to the specified filepath
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"An error occurred while saving the JSON file to {filepath}: {str(e)}")

    def _extract_localization_dict(self, obj, current_path='', result_dict=None):
        if obj is None:
            return None
        
        if result_dict is None:
            result_dict = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if current_path:
                    # if current path ends with
                    if current_path[-1] == "." and key[0]==" " or key[0]==".":
                        new_path = f'{current_path}{key}'
                    else:
                        new_path = f'{current_path}.{key}'
                else:
                    new_path = key

                self._extract_localization_dict(value, new_path, result_dict)

        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                new_path = f"{current_path}{{{index}}}"
                self._extract_localization_dict(item, new_path, result_dict)
        else:
            result_dict[current_path] = obj

        return result_dict

    def _rebuild_nested_json(self, flat_dict):
        nested_json = {}

        for compound_key, value in flat_dict.items():
            # Split the key intelligently based on '.' not followed by whitespace
            keys = [k for k in regex.split(r'\.(?![\s.])', compound_key) if k]
            current_level = nested_json

            for i, key in enumerate(keys):
                if '{' in key and '}' in key:
                    # Split the key on the brackets to get the list name and index
                    list_name, list_index = key.replace('}', '').split('{')
                    list_index = int(list_index)
                    
                    # Ensure the list exists and has enough space for the index
                    if list_name not in current_level:
                        current_level[list_name] = []
                    while len(current_level[list_name]) <= list_index:
                        current_level[list_name].append(None)
                    
                    # If it's the last key, set the value
                    if i == len(keys) - 1:
                        current_level[list_name][list_index] = value
                    else:
                        # Prepare for the next level of nesting
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

    def _generate_concise_diff(self, old_value: str, new_value: str) -> str:
        """
        Generate a human-readable diff between old and new values with context.
        
        Args:
            old_value: Original string
            new_value: Modified string
            
        Returns:
            A formatted string showing the differences with context
        """
        def clean_for_display(text: str) -> str:
            """Format text for display by escaping newlines and reducing whitespace"""
            return text.replace("\n", "\\n").strip()

        def get_context(text: str, pos: int, length: int = 20) -> str:
            """Get surrounding context for a change"""
            start = max(0, pos - length)
            end = min(len(text), pos + length)
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(text) else ""
            return f"{prefix}{text[start:end]}{suffix}"

        s = SequenceMatcher(None, old_value, new_value)
        diff_parts = []
        
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == 'equal':
                continue
                
            # Add context around the change
            context_before = get_context(old_value, i1)
            
            if tag == 'replace':
                diff_parts.append(f"\n      Context: {clean_for_display(context_before)}")
                diff_parts.append(f"      - {clean_for_display(old_value[i1:i2])}")
                diff_parts.append(f"      + {clean_for_display(new_value[j1:j2])}")
                
                # Calculate similarity for this segment
                similarity = SequenceMatcher(None, old_value[i1:i2], new_value[j1:j2]).ratio()
                if similarity > 0.5:  # Only show for somewhat similar changes
                    diff_parts.append(f"      (Similarity: {similarity:.2%})")
                
            elif tag == 'delete':
                diff_parts.append(f"\n      Context: {clean_for_display(context_before)}")
                diff_parts.append(f"      - {clean_for_display(old_value[i1:i2])}")
                
            elif tag == 'insert':
                diff_parts.append(f"\n      Context: {clean_for_display(context_before)}")
                diff_parts.append(f"      + {clean_for_display(new_value[j1:j2])}")

        # If the changes are minimal, suggest a potential regex pattern
        if s.ratio() > 0.8:  # High similarity
            old_parts = [old_value[i1:i2] for tag, i1, i2, _, _ in s.get_opcodes() if tag != 'equal']
            new_parts = [new_value[j1:j2] for tag, _, _, j1, j2 in s.get_opcodes() if tag != 'equal']
            
            if len(old_parts) == 1 and len(new_parts) == 1:
                # Escape special regex characters
                old_pattern = regex.escape(old_parts[0])
                diff_parts.append("\n      Potential regex:")
                diff_parts.append(f"      {old_pattern} -> {new_parts[0]}")

        return '\n'.join(diff_parts)

    def _is_translation_rudimentary(self, en_str: str, pl_str: str, verbose: bool = False) -> bool:
        if not en_str or not pl_str:
            print("Attempted to compare null string(s)")
            return False
        
        def clean_string(s: str, patterns: List[regex.Pattern]) -> str:
            for pattern in patterns:
                s = pattern.sub('', s)
            return s

        # Use the compiled patterns
        en_str_cleaned = clean_string(en_str, self.compiled_patterns)
        pl_str_cleaned = clean_string(pl_str, self.compiled_patterns)

        if(verbose):
            print(en_str_cleaned)
            print(pl_str_cleaned)
            
            matcher = SequenceMatcher(None, en_str_cleaned, pl_str_cleaned)
            print(matcher.ratio())

        # do not check for extremely short strings
        # if min(len(en_str_cleaned), len(pl_str_cleaned)) < 150:
        #     return False

        similarity_threshold = 0.75
        matcher = SequenceMatcher(None, en_str_cleaned, pl_str_cleaned)
        similarity = matcher.ratio()
        return similarity >= similarity_threshold

    def _auto_pretranslate(self, en_str: Optional[str]) -> Optional[str]:
        def save_and_replace_brackets(text):
            """
            Detects text encapsulated in square brackets, including nested ones,
            replaces them with placeholders, and saves the original texts.

            :param text: The original text to process.
            :return: Modified text with placeholders, and a list of the original bracketed texts.
            """
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
                    
                    # skip until the outermost bracket
                    if open_brackets:
                        continue
                    
                    encapsulated = text[start:i+1]
                    bracketed_texts.append(encapsulated)
                    placeholder = generate_placeholder(len(bracketed_texts) - 1)
                    placeholders.append((start, i, placeholder))
                i += 1

            # Replace the bracketed text with placeholders
            for start, end, placeholder in reversed(placeholders):
                text = text[:start] + placeholder + text[end+1:]

            return text, bracketed_texts

        def restore_bracketed_text(modified_text, bracketed_texts):
            """
            Restores the originally bracketed text using the placeholders.

            :param modified_text: The text after regex modifications.
            :param bracketed_texts: The list of original bracketed texts.
            :return: The final text with the original bracketed texts restored.
            """
            for i, original_text in enumerate(bracketed_texts):
                modified_text = modified_text.replace(f"__PLACEHOLDER_{i}__", original_text)
            return modified_text
        
        def replace_with_patterns(text: str, compiled_replacements) -> str:
            """
            Replaces occurrences in 'text' using pre-compiled patterns
            
            :param text: The original text to process.
            :param compiled_replacements: A list of tuples where the first element is the compiled regex pattern
                                        and the second element is the replacement pattern.
            :return: The modified text after all replacements.
            """
            for pattern, replacement in compiled_replacements:
                text = pattern.sub(replacement, text)
            return text

        if en_str is None:
            print("Cannot pretranslate empty string")
            return en_str

        # Step 1: Save and replace bracketed sections with placeholders
        text_with_placeholders, bracketed_texts = save_and_replace_brackets(en_str)

        # Step 2: Apply regex replacements using compiled patterns
        modified_text = replace_with_patterns(text_with_placeholders, self.compiled_replacement_patterns)

        # Step 3: Restore the original bracketed sections
        final_text = restore_bracketed_text(modified_text, bracketed_texts)

        return final_text
    
    def _update_localization(self):
        # Count occurrences of each value in both dictionaries
        pl_path_basename = os.path.basename(self.pl_path)
        en_old_keys_set = set(self.en_old_extracted.keys())
        en_new_keys_set = set(self.en_extracted.keys())
        
        # Pre-calculate value mappings
        value_mappings = self._calculate_value_mappings()
        
        # Process new/updated translations
        self._process_translations(value_mappings, pl_path_basename)
        
        # Remove obsolete keys
        self._remove_obsolete_keys(en_old_keys_set, en_new_keys_set, pl_path_basename)

    def _calculate_value_mappings(self):
        """Pre-calculate all value mappings for faster lookup"""
        # Count occurrences of each value in both dictionaries
        old_value_counts = Counter(self.en_old_extracted.values())
        new_value_counts = Counter(self.en_extracted.values())

        # Identify unique values in both dictionaries
        unique_old_values = {
            value for value, count in old_value_counts.items() 
            if count == 1
        }
        unique_new_values = {
            value for value, count in new_value_counts.items() 
            if count == 1
        }

        # Reverse mapping for unique values only
        return {
            'old_to_key': {
                value: key 
                for key, value in self.en_old_extracted.items() 
                if value in unique_old_values
            },
            'unique_new_values': unique_new_values
        }

    def _process_translations(self, value_mappings, pl_path_basename):
        """Process all translations with optimized lookups"""
        old_to_key = value_mappings['old_to_key']
        unique_new_values = value_mappings['unique_new_values']

        # Cache frequently accessed methods
        auto_pretranslate = self._auto_pretranslate
        is_translation_rudimentary = self._is_translation_rudimentary
        
        for new_key, new_value in tqdm(
            self.en_extracted.items(), 
            desc=f"Processing {pl_path_basename}"
        ):
            if new_key in self.pl_extracted:
                # Key is already up to date
                if self.pl_extracted[new_key] == new_value:
                    continue
                
                # if the key exists in translation, and the value changed
                if new_value != self.en_old_extracted.get(new_key):
                    self._handle_value_update(
                        new_key, 
                        new_value, 
                        auto_pretranslate,
                        is_translation_rudimentary
                    )
                    continue

            # rename key if both before and after the value is unique
            old_key = old_to_key.get(new_value)
            if old_key and old_key != new_key and new_value in unique_new_values:
                self._handle_key_rename(new_key, old_key, pl_path_basename)
                continue

            # if value does not exist in translation, add it
            if new_key not in self.pl_extracted:
                self.pl_extracted[new_key] = auto_pretranslate(new_value)
                self.new_keys.append(new_key)

    def _handle_value_update(self, new_key, new_value, auto_pretranslate, is_translation_rudimentary):
        """Handle updates to existing translations"""
        old_en_value = self.en_old_extracted.get(new_key)
        current_pl = self.pl_extracted.get(new_key)

        # if value was kept in english, update it outright
        if current_pl == old_en_value:
            self.pl_extracted[new_key] = auto_pretranslate(new_value)
            self.updated_eng_keys.append(new_key)
            return

        # if translation is rudimentary (usually due to the effect of global regex operations) auto-update it to save time
        old_en_pretranslated = auto_pretranslate(old_en_value)
        if is_translation_rudimentary(old_en_pretranslated, current_pl):
            self.pl_extracted[new_key] = auto_pretranslate(new_value)
            self.rudimentary_translations_updated.append(new_key)
            return

        # else mark it as an outdated translation that needs manual correction
        diff_string = self._generate_concise_diff(old_en_value, new_value)
        self.outdated_keys.append((new_key, diff_string))

    def _handle_key_rename(self, new_key, old_key, pl_path_basename):
        """Handle key rename operations"""
        # double-check for translated entry existence
        if old_key not in self.pl_extracted:
            print(f"Did not find old key {old_key} in polish {pl_path_basename}. "
                  "It may have been updated already")
            return

        self.pl_extracted[new_key] = self.pl_extracted.get(old_key)
        self.renamed_keys.append((old_key, new_key))

    def _remove_obsolete_keys(self, en_old_keys_set, en_new_keys_set, pl_path_basename):
        """Remove obsolete keys efficiently"""
        # remove obsolete keys
        obsolete_keys = en_old_keys_set - en_new_keys_set
        
        if not obsolete_keys:
            return

        for old_key in tqdm(
            obsolete_keys,
            desc=f"Deleting obsolete keys in {pl_path_basename}",
            leave=False
        ):
            self.pl_extracted.pop(old_key, None)
            self.removed_keys.append(old_key)

    def _validate_keys_match(self, path=''):
        errors = []

        for key in self.en_extracted.keys():
            current_path = f"{path}.{key}" if path else key
            if key not in self.pl_extracted:
                errors.append(f"Missing key in target: {current_path}")
            else:
                if isinstance(self.en_extracted[key], dict) and isinstance(self.pl_extracted[key], dict):
                    errors.extend(self._validate_keys_match(self.en_extracted[key], self.pl_extracted[key], current_path))
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
        """Main processing method for localization updates"""
        # Load and validate input files
        if not self._load_and_validate_files():
            return

        pl_path_basename = os.path.basename(self.pl_path)
        
        # Handle different processing modes
        if perform_regex_translate:
            self._apply_regex_translations(pl_path_basename)
        else:
            # Skip if translation is already up to date
            if self.pl_extracted == self.en_extracted:
                return
            self._update_localization()

        # Skip further processing if no changes and not doing regex translation
        if not self._has_changes() and not perform_regex_translate:
            return

        # Log changes and validate results
        self._log_changes(pl_path_basename)
        
        # Sort and save the final dictionary
        self._sort_and_save_translations()

    def _load_and_validate_files(self):
        """Load and validate all required localization files"""
        self.en_old_extracted = self._extract_localization_dict(self._get_file_from_directory(self.en_old_path))
        self.en_extracted = self._extract_localization_dict(self._get_file_from_directory(self.en_path))
        self.pl_extracted = self._extract_localization_dict(self._get_file_from_directory(self.pl_path))

        if self.en_old_extracted is None or self.en_extracted is None or self.pl_extracted is None:
            logging.info(f"{os.path.basename(self.pl_path)}:")
            logging.error("Unable to proceed due to missing data.")
            return False
        return True

    def _apply_regex_translations(self, pl_path_basename):
        """Apply regex translations to all records"""
        for key, value in tqdm(self.pl_extracted.items(), 
                             desc=f"Regex-translating {pl_path_basename}"):
            self.pl_extracted[key] = self._auto_pretranslate(self.pl_extracted[key])

    def _has_changes(self):
        """Check if any changes were made during processing"""
        return any([
            self.new_keys,
            self.removed_keys,
            self.renamed_keys,
            self.updated_eng_keys,
            self.outdated_keys
        ])

    def _log_changes(self, pl_path_basename):
        """Log all changes if verbose or if there are outdated keys"""
        if not (self.verbose or self.outdated_keys):
            return

        # Log the processed file name
        logging.info(f"{pl_path_basename}:")
        
        change_logs = [
            ("Added keys", self.new_keys),
            ("Deleted keys", self.removed_keys),
            ("Updated english keys", self.updated_eng_keys),
            ("Rudimentary translations updated", self.rudimentary_translations_updated)
        ]

        # Log simple changes if verbose
        if self.verbose:
            for description, items in change_logs:
                if items:
                    logging.info(f"  {description}: {len(items)}")
                    for item in items:
                        logging.info(f"    {item}")

            # Log renamed keys separately due to different structure
            if self.renamed_keys:
                logging.info(f"  Renamed keys (transferred): {len(self.renamed_keys)}")
                for old_key, new_key in self.renamed_keys:
                    logging.info(f"    {old_key} -> {new_key}")

        # Always log outdated keys
        if self.outdated_keys:
            logging.info(f"  Outdated records: {len(self.outdated_keys)}")
            for key, diff in self.outdated_keys:
                logging.info(f"    Key: {key}\n    Diff:{diff}\n")

        # Validate and log results
        self._validate_and_log_results()

    def _validate_and_log_results(self):
        """Validate and log the results of key matching"""
        validation_errors = self._validate_keys_match()
        if validation_errors:
            for error in validation_errors:
                logging.error(error)
            logging.error("Validation failed, the keys in English and Polish files do not match.")
        else:
            logging.info("Validation successful, all keys match.")

    def _sort_and_save_translations(self):
        """Sort translations according to template and save to file"""
        # Sort the dictionary according to template
        ordered_pl = {
            key: self.pl_extracted.get(key, None)
            for key in self.en_extracted.keys()
        }
        
        self.pl_extracted = ordered_pl
        logging.info("\n")

        # Save the final result
        self._save_file_to_directory(
            self.pl_path,
            self._rebuild_nested_json(self.pl_extracted)
        )