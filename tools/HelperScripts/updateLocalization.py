import os
import json
import logging

import regex
from collections import Counter
from tqdm import tqdm
import datetime
import shutil
import subprocess
import argparse

import difflib
from difflib import SequenceMatcher

class LocalizationUpdater:
    
    def __init__(self, en_old_path, en_path, pl_path):
        # filepaths
        self.en_old_path = en_old_path
        self.en_path = en_path
        self.pl_path = pl_path

        # data containers
        self.en_old_extracted = {}
        self.en_extracted = {}
        self.pl_extracted = {}

        # key operation logs
        self.new_keys = []
        self.removed_keys = []
        self.renamed_keys = []
        self.outdated_keys = []
        self.updated_eng_keys = []
        self.rudimentary_translations_updated = []

        # Auto-translated patterns
        # PYTHON READS THE JSON STRING WITH ITS ESCAPE CHARACTERS ACCOUNTED FOR
        # Escape signs in JSON need to be accounted for in regex (usually reduced/removed)
        self.replacement_patterns = [
            # Success degrees
            (r'>Critical Success<', r'>Krytyczny Sukces<'),
            (r'>Success<', r'>Sukces<'),
            (r'>Critical Failure<', r'>Krytyczna Porażka<'),
            (r'>Failure<', r'>Porażka<'),
            # Activation keywords
            (r'>Activate<', r'>Aktywacja<'),
            (r'>Trigger<', r'>Aktywator<'),
            (r'>Frequency<', r'>Częstotliwość<'),
            # Effect keywords
            (r'>Effect<', r'>Efekt<'),
            (r'>Secondary Effect<', r'>Efekt Dodatkowy<'),
            (r'Spell Effect:', r'Efekt Zaklęcia:'),
            (r'Crit Effect:', r'Efekt Krytyczny:'),
            (r'Effect:', r'Efekt:'),
            (r'>Maximum Duration<', r'>Maksymalny Czas Trwania<'),
            (r'>(Prerequisites|Requirements)<', r'>Wymagania<'),
            (r'>Special<', r'>Specjalne<'),
            (r'>Craft Requirements<', r'>Wymagania Wytwarzania<'),
            # Material details
            (r'<h2>([^<]*) Items</h2>\n<table', r'<h2>Przedmioty z \1</h2>\n<table'),
            (r'<th>([^<]*) Items</th>', r'<th>Przedmioty z \1</th>'),
            (r'>Hardness<', r'>Twardość<'),
            (r'>HP<', r'>PŻ<'),
            (r'>BT<', r'>PU<'),
            (r'>Thin Items<', r'>Cienkie Przedmioty<'),
            (r'>Items<', r'>Przedmioty<'),
            (r'>Structures<', r'>Struktury<'),
            (r'>Standard\-grade<', r'>Standardowej Jakości<'),
            (r'>High\-grade<', r'>Wysokiej Jakości<'),
            # Spells
            (r'>Cantrip<', r'>Sztuczka<'),
            (r'>Spell<', r'>Zaklęcie<'),
            (r'>Spells<', r'>Zaklęcia<'),
            # Poisons diseases
            (r'>Saving Throw<', r'>Rzut Obronny<'),
            (r'>Onset<', r'>Nadejście Objawów<'),
            (r'>Stage ([0-9]+)<', r'>Stadium \1<'),
            (r'\(Injury\)', r'(Rana)'),
            (r'\(Contact\)', r'(Dotyk)'),
            (r'\(Inhaled\)', r'(Wdychanie)'),
            (r'\(Ingested\)', r'(Spożycie)'),
            # Activation details. Must be after the activate
            (r'<p><strong>Aktywacja</strong> <span class=\"action-glyph\">(\S+)</span> ([^<]*)Interact([^<]*)</p>',
             r'<p><strong>Aktywacja</strong> <span class="action-glyph">\1</span> \2Interakcja\3</p>'),
            (r'<p><strong>Aktywacja</strong> <span class=\"action-glyph\">(\S+)</span> ([^<]*)Cast a Spell([^<]*)</p>',
             r'<p><strong>Aktywacja</strong> <span class="action-glyph">\1</span> \2Rzucenie Zaklęcia\3</p>'),
            (r'<p><strong>Aktywacja</strong> <span class=\"action-glyph\">(\S+)</span> ([^<]*)command([^<]*)</p>',
             r'<p><strong>Aktywacja</strong> <span class="action-glyph">\1</span> \2komenda\3</p>'),
            (r'<p><strong>Aktywacja</strong> <span class=\"action-glyph\">(\S+)</span> ([^<]*)envision([^<]*)</p>',
             r'<p><strong>Aktywacja</strong> <span class="action-glyph">\1</span> \2wyobrażenie\3</p>'),
            (r'<p><strong>Aktywacja</strong> <span class=\"action-glyph\">(\S+)</span> ([^<]*)Strike([^<]*)</p>',
             r'<p><strong>Aktywacja</strong> <span class="action-glyph">\1</span> \2Cios\3</p>'),
            # Frequency details. Must be after frequency
            (r'<p><strong>Częstotliwość</strong> once per day</p>',
             r'<p><strong>Częstotliwość</strong> raz na dzień</p>'),
            (r'<p><strong>Częstotliwość</strong> once per day, plus overcharge</p>',
             r'<p><strong>Częstotliwość</strong> raz na dzień, plus przeciążenie</p>'),
            # Effect details. Must be after effect.
            (r'<p><strong>Efekt</strong> You cast (@UUID\[Compendium\.pf2e\.spells-srd\.Item\.([a-zA-Z0-9]*)\]\{([a-zA-Z0-9 \p{L}]*)\}).</p>',
             r'<p><strong>Efekt</strong> Rzucasz \1.</p>'),
            # Crafting
            (r'Supply a casting of the spell at the listed (rank|level)\.',
             r'Dostarcz rzucenie docelowego zaklęcia na podanym kręgu.'),
            (r'Supply a casting of a spell of the appropriate (rank|level)\.',
             r'Dostarcz rzucenie docelowego zaklęcia na odpowiednim kręgu.'),
            (r'Supply one casting of all listed levels of all listed spells\.',
             r'Dostarcz po jednym rzuceniu wszystkich wymienionych zaklęć.'),
             # Styling and punctuation
            (r' -([0-9]+)', r' –\1'),
            (r'(\S)—(\S)', r'\1 — \2'),
        ]


    def get_file_from_directory(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"An error occurred while loading the JSON file: {filepath}: {str(e)}")
            return None

    def save_file_to_directory(self, filepath, data):
        try:
            # Ensure the directory of the file exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the data to the specified filepath
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
                    # if current path ends with
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

    def generate_concise_diff(self, old_value, new_value):

        # Create a sequence matcher
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
        
        # Regex to match and exclude
        regex_patterns = [
             r'@[^\]]+\[([^\[]|\[\S+\])+\]',
             r'(?<!\])\{[^\{]+\}',
             r'(?<!\[)\[[^\[\]]+\]', # single suare, to remove damage
             r'\[\[[^(\]\])]+\]\]', # afterwards, double square, to remove formulas
             r'<[^<]+>',
             r'\\n'
        ]

        # Function to clean the string by removing all patterns
        def clean_string(s, patterns):
            for pattern in patterns:
                s = regex.sub(pattern, '', s)
            return s

        # Remove matched patterns from the strings
        en_str_cleaned = clean_string(en_str, regex_patterns)
        pl_str_cleaned = clean_string(pl_str, regex_patterns)

        if(verbose):
            print(en_str_cleaned)
            print(pl_str_cleaned)
            
            matcher = SequenceMatcher(None, en_str_cleaned, pl_str_cleaned)
            print(matcher.ratio())

        # do not check for extremely short strings
        if min(len(en_str_cleaned), len(pl_str_cleaned)) < 150:
            return False

        similarity_threshold = 0.75
        matcher = SequenceMatcher(None, en_str_cleaned, pl_str_cleaned)
        similarity = matcher.ratio()
        return similarity >= similarity_threshold

    def auto_pretranslate(self, en_str):
        def replace_with_patterns(text, replacements):
            """
            Replaces occurrences in 'text' based on a list of ('pattern', 'replacement') tuples.
            
            :param text: The original text to process.
            :param replacements: A list of tuples where the first element is the regex pattern
                                to match and the second element is the replacement pattern.
            :return: The modified text after all replacements.
            """
            for pattern, replacement in replacements:
                text = regex.sub(pattern, replacement, text)
            return text

        # Process the text
        return replace_with_patterns(en_str, self.replacement_patterns)
    
    def update_localization(self):
        # Count occurrences of each value in both dictionaries
        old_value_counts = Counter(self.en_old_extracted.values())
        new_value_counts = Counter(self.en_extracted.values())

        # Identify unique values in both dictionaries
        unique_old_values = {value for value, count in old_value_counts.items() if count == 1}
        unique_new_values = {value for value, count in new_value_counts.items() if count == 1}

        # Reverse mapping for unique values only
        old_value_to_key = {value: key for key, value in self.en_old_extracted.items() if value in unique_old_values}
        new_value_to_key = {value: key for key, value in self.en_extracted.items() if value in unique_new_values}

        for new_key, new_value in tqdm(self.en_extracted.items(), desc=f"Processing new keys in {os.path.basename(self.pl_path)}"):
            
            # Key is already up to date
            if new_key in self.pl_extracted and self.pl_extracted.get(new_key) == new_value:
                continue
            
            # rename key if both before and after the value is unique
            old_key = old_value_to_key.get(new_value, None)
            if old_key and old_key != new_key and new_value in unique_new_values:
                # double-check for translated entry existence
                if old_key not in self.pl_extracted:
                    print(f"Did not find old key {old_key} in polish {os.path.basename(self.pl_path)}. It may have been updated already")
                else:
                    self.pl_extracted[new_key] = self.pl_extracted.get(old_key, None)
                    self.renamed_keys.append((old_key, new_key))
            
            # if the key exists in translation, and the value changed
            elif (new_key in self.pl_extracted and
                new_value != self.en_old_extracted.get(new_key, None)):
                
                # if value was kept in english, update it outright
                if self.pl_extracted.get(new_key) == self.en_old_extracted.get(new_key):
                    self.pl_extracted[new_key] = self.auto_pretranslate(new_value)
                    self.updated_eng_keys.append(new_key)
                # if translation is rudimentary (usually due to the effect of global regex operations) auto-update it to save time
                elif self.is_translation_rudimentary(self.en_old_extracted.get(new_key, None), self.pl_extracted.get(new_key)):
                    self.pl_extracted[new_key] = self.auto_pretranslate(new_value)
                    self.rudimentary_translations_updated.append(new_key)
                # else mark it as an outdated translation that needs manual correction
                else:
                    old_value = self.en_old_extracted.get(new_key, "")
                    diff_string = self.generate_concise_diff(old_value, new_value)
                    self.outdated_keys.append((new_key, diff_string))

            # if value does not exist in translation, add it
            elif new_key not in self.pl_extracted:
                self.pl_extracted[new_key] = self.auto_pretranslate(new_value)
                self.new_keys.append(new_key)

        # remove obsolete keys
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

        if (not perform_regex_translate):
            #Not translated and already up to date. Skipping!
            if self.pl_extracted == self.en_extracted:
                return
            
            self.update_localization()
        else:
            # apply regex translation to all records
            for key, value in tqdm(self.pl_extracted.items(), desc=f"Regex-translating {os.path.basename(self.pl_path)}"):
                self.pl_extracted[key] = self.auto_pretranslate(self.pl_extracted[key])

        # if no keys were modified, return
        if not any([self.new_keys, self.removed_keys, self.renamed_keys, self.updated_eng_keys, self.outdated_keys]) and not perform_regex_translate:
            return

        # Log the processed file name
        logging.info(f"{os.path.basename(self.pl_path)}:")
        
        if self.new_keys:
            logging.info(f"  Added keys: {len(self.new_keys)}")
            for key in self.new_keys:
                logging.info(f"    {key}")

        if self.removed_keys:
            logging.info(f"  Deleted keys: {len(self.removed_keys)}")
            for key in self.removed_keys:
                logging.info(f"    {key}")

        if self.renamed_keys:
            logging.info(f"  Renamed keys (transferred): {len(self.renamed_keys)}")
            for old_key, new_key in self.renamed_keys:
                logging.info(f"    {old_key} -> {new_key}")

        if self.updated_eng_keys:
            logging.info(f"  Updated english keys: {len(self.updated_eng_keys)}")
            for key in self.updated_eng_keys:
                logging.info(f"    {key}")

        if self.rudimentary_translations_updated:
            logging.info(f"  Rudimentary translations updated: {len(self.rudimentary_translations_updated)}")
            for key in self.rudimentary_translations_updated:
                logging.info(f"    {key}")

        if self.outdated_keys:
            logging.info(f"  Outdated records: {len(self.outdated_keys)}")
            for key, diff in self.outdated_keys:  # Unpack key and diff_string
                logging.info(f"    Key: {key}\n    Diff:{diff}\n")


        validation_errors = self.validate_keys_match()
        if validation_errors:
            for error in validation_errors:
                logging.error(error)
            logging.error("Validation failed, the keys in English and Polish files do not match.")
        else:
            logging.info("Validation successful, all keys match.")
        
        # sort the dictionary
        ordered_pl = {}

        # Iterate over keys in the template dictionary
        for key in self.en_extracted.keys():
            ordered_pl[key] = self.pl_extracted.get(key, None)
        
        self.pl_extracted = ordered_pl

        logging.info("\n")

        self.save_file_to_directory(self.pl_path, self.rebuild_nested_json(self.pl_extracted))

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
    # Setup logging configuration
    log_directory = "tools/HelperScripts/Logs"
    os.makedirs(log_directory, exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(log_directory, f"LocalizationUpdate_{current_time}.log")
    logging.basicConfig(level=logging.INFO, filename=log_filename, filemode='w', format='%(message)s')

    # Set up the argument parser
    parser = argparse.ArgumentParser(description='Run the script with optional update source data flag.')
    parser.add_argument('--UpdateSourceData', action='store_true', help='Update source data if set to true.')
    parser.add_argument('--PreformRegexTranslate', action='store_true', help='Forces re-processing all strings by regex translations.')

    # Parse the arguments
    args = parser.parse_args()

    # The flag is False by default, True if --UpdateSourceData is used in the command line
    update_source_data = args.UpdateSourceData

    # The flag is False by default, True if --UpdateSourceData is used in the command line
    preform_regex_translate = args.PreformRegexTranslate

    # Define sets of file paths
    file_sets = []
    
    temp_en_old_directory = "tools/HelperScripts/OldLocale/"
    core_en_directory = "translation/en/"
    core_pl_directory = "translation/pl/"
    
    en_to_pl_file_pairs =  [
        ("en", "pl"),
        ("action-en", "action-pl"),
        ("re-en", "re-pl"),
        ("dictionary", "dictionary"),
        ("kingmaker-en", "kingmaker-pl"),
        ("compendium/action-macros", "compendium/pf2e.action-macros"),
        ("compendium/actions","compendium/pf2e.actionspf2e"),
        ("compendium/adventure-specific-actions","compendium/pf2e.adventure-specific-actions"),
        ("compendium/ancestries","compendium/pf2e.ancestries"),
        ("compendium/ancestryfeatures","compendium/pf2e.ancestryfeatures"),
        ("compendium/backgrounds","compendium/pf2e.backgrounds"),
        ("compendium/bestiary-ability-glossary-srd","compendium/pf2e.bestiary-ability-glossary-srd"),
        ("compendium/bestiary-effects","compendium/pf2e.bestiary-effects"),
        ("compendium/bestiary-family-ability-glossary","compendium/pf2e.bestiary-family-ability-glossary"),
        ("compendium/boons-and-curses","compendium/pf2e.boons-and-curses"),
        ("compendium/campaign-effects","compendium/pf2e.campaign-effects"),
        ("compendium/classes","compendium/pf2e.classes"),
        ("compendium/classfeatures","compendium/pf2e.classfeatures"),
        ("compendium/conditions","compendium/pf2e.conditionitems"),
        ("compendium/criticaldeck","compendium/pf2e.criticaldeck"),
        ("compendium/deities","compendium/pf2e.deities"),
        ("compendium/equipment-effects","compendium/pf2e.equipment-effects"),
        ("compendium/equipment","compendium/pf2e.equipment-srd"),
        ("compendium/familiar-abilities","compendium/pf2e.familiar-abilities"),
        ("compendium/feat-effects","compendium/pf2e.feat-effects"),
        ("compendium/feats","compendium/pf2e.feats-srd"),
        ("compendium/hazards","compendium/pf2e.hazards"),
        ("compendium/heritages","compendium/pf2e.heritages"),
        ("compendium/iconics","compendium/pf2e.iconics"),
        ("compendium/journals","compendium/pf2e.journals"),
        ("compendium/kingmaker-features","compendium/pf2e.kingmaker-features"),
        ("compendium/other-effects","compendium/pf2e.other-effects"),
        ("compendium/paizo-pregens","compendium/pf2e.paizo-pregens"),
        ("compendium/macros","compendium/pf2e.pf2e-macros"),
        ("compendium/rollable-tables","compendium/pf2e.rollable-tables"),
        ("compendium/spell-effects","compendium/pf2e.spell-effects"),
        ("compendium/spells","compendium/pf2e.spells-srd"),
        ("compendium/vehicles","compendium/pf2e.vehicles"),
        #Bestiary
        ("actors/abomination-vaults-bestiary","compendium/pf2e.abomination-vaults-bestiary"),
        ("actors/age-of-ashes-bestiary","compendium/pf2e.age-of-ashes-bestiary"),
        ("actors/agents-of-edgewatch-bestiary","compendium/pf2e.agents-of-edgewatch-bestiary"),
        ("actors/blog-bestiary","compendium/pf2e.blog-bestiary"),
        ("actors/blood-lords-bestiary","compendium/pf2e.blood-lords-bestiary"),
        ("actors/book-of-the-dead-bestiary","compendium/pf2e.book-of-the-dead-bestiary"),
        ("actors/crown-of-the-kobold-king-bestiary","compendium/pf2e.crown-of-the-kobold-king-bestiary"),
        ("actors/extinction-curse-bestiary","compendium/pf2e.extinction-curse-bestiary"),
        ("actors/fists-of-the-ruby-phoenix-bestiary","compendium/pf2e.fists-of-the-ruby-phoenix-bestiary"),
        ("actors/gatewalkers-bestiary","compendium/pf2e.gatewalkers-bestiary"),
        ("actors/kingmaker-bestiary","compendium/pf2e.kingmaker-bestiary"),
        ("actors/malevolence-bestiary","compendium/pf2e.malevolence-bestiary"),
        ("actors/menace-under-otari-bestiary","compendium/pf2e.menace-under-otari-bestiary"),
        ("actors/mwangi-expanse-bestiary","compendium/pf2e.mwangi-expanse-bestiary"),
        ("actors/night-of-the-gray-death-bestiary","compendium/pf2e.night-of-the-gray-death-bestiary"),
        ("actors/one-shot-bestiary","compendium/pf2e.one-shot-bestiary"),
        ("actors/outlaws-of-alkenstar-bestiary","compendium/pf2e.outlaws-of-alkenstar-bestiary"),
        ("actors/pathfinder-bestiary-2","compendium/pf2e.pathfinder-bestiary-2"),
        ("actors/pathfinder-bestiary-3","compendium/pf2e.pathfinder-bestiary-3"),
        ("actors/pathfinder-bestiary","compendium/pf2e.pathfinder-bestiary"),
        ("actors/pfs-introductions-bestiary","compendium/pf2e.pfs-introductions-bestiary"),
        ("actors/blog-bestiary","compendium/pf2e.blog-bestiary"),
        ("actors/pfs-season-1-bestiary","compendium/pf2e.pfs-season-1-bestiary"),
        ("actors/pfs-season-2-bestiary","compendium/pf2e.pfs-season-2-bestiary"),
        ("actors/pfs-season-3-bestiary","compendium/pf2e.pfs-season-3-bestiary"),
        ("actors/pfs-season-4-bestiary","compendium/pf2e.pfs-season-4-bestiary"),
        ("actors/pfs-season-5-bestiary","compendium/pf2e.pfs-season-5-bestiary"),
        ("actors/rage-of-elements-bestiary","compendium/pf2e.rage-of-elements-bestiary"),
        ("actors/rusthenge-bestiary","compendium/pf2e.rusthenge-bestiary"),
        ("actors/season-of-ghosts-bestiary","compendium/pf2e.season-of-ghosts-bestiary"),
        ("actors/shadows-at-sundown-bestiary","compendium/pf2e.shadows-at-sundown-bestiary"),
        ("actors/sky-kings-tomb-bestiary","compendium/pf2e.sky-kings-tomb-bestiary"),
        ("actors/stolen-fate-bestiary","compendium/pf2e.stolen-fate-bestiary"),
        ("actors/strength-of-thousands-bestiary","compendium/pf2e.strength-of-thousands-bestiary"),
        ("actors/the-enmity-cycle-bestiary","compendium/pf2e.the-enmity-cycle-bestiary"),
        ("actors/the-slithering-bestiary","compendium/pf2e.the-slithering-bestiary"),
        ("actors/troubles-in-otari-bestiary","compendium/pf2e.troubles-in-otari-bestiary"),
        
    ]

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

    if(update_source_data):
        # update the source files
        print("Running the pack extractor...")
        run_js_script("src/pack-extractor/pack-extractor.js")

    for en_old, en, pl in file_sets:
        updater = LocalizationUpdater(en_old, en, pl)
        updater.process(preform_regex_translate)
    
    # clean the OldLocale folder
    shutil.rmtree(temp_en_old_directory)

if __name__ == "__main__":
    main()