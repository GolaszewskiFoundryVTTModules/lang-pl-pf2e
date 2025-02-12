# Basic formatting and typography
formatting_patterns = [
    (r' -(\d+)', r' –\1'),
    (r'(\S)—(\S)', r'\1 — \2'),
    (r'([„”“])', r'"'),
    (r'([’])', r"'"),
    (r'>\n<', r'><'),
]

# Game mechanics and basic rules
game_mechanics_patterns = [
    # Ordinals
    (r'(\d+)(st|nd|rd|th)-([Ll]evel)', lambda m: f"{m.group(1)}. {'Poziomu' if m.group(3)[0].isupper() else 'poziomu'}"),
    (r'(\d+)(st|nd|rd|th)-([Rr]ank)', lambda m: f"{m.group(1)}. {'Kręgu' if m.group(3)[0].isupper() else 'kręgu'}"),
    # Dice notation
    (r'(\d*)d(\d+)', r'\1k\2'),
    # Success degrees
    (r'(>|\()Critical Success(<|\))', r'\1Krytyczny Sukces\2'),
    (r'(>|\()Success(<|\))', r'\1Sukces\2'),
    (r'(>|\()Critical Failure(<|\))', r'\1Krytyczna Porażka\2'),
    (r'(>|\()Failure(<|\))', r'\1Porażka\2'),
]


# Define condition translations
condition_translations = {
    'Invisible': 'Niewidzialny',
    'Blinded': 'Oślepiony',
    'Broken': 'Uszkodzony',
    'Concealed': 'Przysłonięty',
    'Confused': 'Zdezorientowany',
    'Controlled': 'Kontrolowany',
    'Dazzled': 'Zamroczony',
    'Deafened': 'Ogłuchły',
    'Doomed': 'Zgubiony',
    'Encumbered': 'Przeciążony',
    'Fascinated': 'Zafascynowany',
    'Fatigued': 'Wyczerpany',
    'Fleeing': 'Uciekający',
    'Friendly': 'Przyjazny',
    'Grabbed': 'Pochwycony',
    'Helpful': 'Pomocny',
    'Hidden': 'Schowany',
    'Hostile': 'Wrogi',
    'Immobilized': 'Unieruchomiony',
    'Indifferent': 'Obojętny',
    'Observed': 'Postrzegany',
    'Paralyzed': 'Sparaliżowany',
    'Petrified': 'Spetryfikowany',
    'Prone': 'Powalony',
    'Restrained': 'Spętany',
    'Unconscious': 'Nieprzytomny',
    'Undetected': 'Niewykryty',
    'Unfriendly': 'Nieprzyjazny',
    'Off-Guard': 'Opuszczona Garda'
}

# Generate patterns from translations
status_conditions = [
    (rf'\{{{en}\}}', rf'{{{pl}}}')
    for en, pl in condition_translations.items()
]

leveled_condition_translations = {
    'Sickened': 'Zemdlony',
    'Clumsy': 'Niezdarny',
    'Enfeebled': 'Osłabiony',
    'Drained': 'Wyniszczony',
    'Stupefied': 'Ogłupiony',
    'Stunned': 'Ogłuszony',
    'Wounded': 'Ranny',
    'Dying': 'Umierający',
    'Frightened': 'Przerażony',
    'Quickened': 'Przyspieszony',
    'Slowed': 'Spowolniony'
}

leveled_conditions = [
    (rf'\{{{en}(| \d+)\}}', rf'{{{pl}\1}}')
    for en, pl in leveled_condition_translations.items()
]

# Item variants and types
item_patterns = [
    (r'\(Minor\)', r'(Drobny)'),
    (r'\(Lesser\)', r'(Mniejszy)'),
    (r'\(Moderate\)', r'(Umiarkowany)'),
    (r'\(Standard\)', r'(Standardowy)'),
    (r'\(Greater\)', r'(Większy)'),
    (r'\(Major\)', r'(Potężny)'),
    (r'\(Supreme\)', r'(Wyjątkowy)'),
    (r'\(Type (\S+)\)', r'(Typ \1)'),
]

# Religious elements
religious_elements = [
    (r'>Edicts<', r'>Edykty<'),
    (r'>Anathema<', r'>Anatemy<'),
    (r'>Areas of Concern<', r'>Obszary Wpływów<'),
    (r'>Covenant Members<', r'>Członkowie Przymierza<'),
    (r'>Title<', r'>Przydomek<'),
    (r'>Religious Symbol<', r'>Symbol Religijny<'),
    (r'>Sacred Animal<', r'>Święte Zwierzę<'),
    (r'>Sacred Color<', r'>Święta Barwa<'),
    (r'>Sacred Colors?<', lambda m: '>Święte Barwy<' if m.group(0).endswith('s<') else '>Święta Barwa<'),
]

# Activation and trigger patterns
activation_patterns = [
    (r'>Activate<', r'>Aktywacja<'),
    (r'>Activate — ([\p{L}\d ]*)<', r'>Aktywacja — \1<'),
    (r'>Trigger<', r'>Aktywator<'),
    (r'>Frequency<', r'>Częstotliwość<'),
]

# Effect-related patterns
effect_patterns = [
    (r'>Effect<', r'>Efekt<'),
    (r'>Secondary Effect<', r'>Efekt Dodatkowy<'),
    (r'Spell Effect:', r'Efekt Zaklęcia:'),
    (r'Crit Effect:', r'Efekt Krytyczny:'),
    (r'Effect:', r'Efekt:'),
    (r'Stance:', r'Postawa:'),
    (r'>Maximum Duration<', r'>Maksymalny Czas Trwania<'),
]

# Requirement patterns
requirement_patterns = [
    (r'>(Prerequisites|Requirements|Requirement)<', r'>Wymagania<'),
    (r'>Special<', r'>Specjalne<'),
    (r'>Craft Requirements<', r'>Wymagania Wytwarzania<'),
    (r'>Cost<', r'>Koszt<'),
    (r'>Price<', r'>Cena<'),
    (r'>Prerequisite<', r'>Wymaganie<'),
    (r'>Access<', r'>Dostęp<'),
    (r'>Destruction<', r'>Zniszczenie<'),
]

# Usage and equipment patterns
usage_patterns = [
    (r'>Usage<', r'>Zastosowanie<'),
    (r'<p><strong>Zastosowanie</strong> affixed to armor</p>',
        r'<p><strong>Zastosowanie</strong> mocowanie do pancerza</p>'),
]

# Creature stats and attributes
creature_patterns = [
    (r'>Level<', r'>Poziom<'),
    (r'>Hit Points<', r'>Punkty Żywotności<'),
    (r'>Senses<', r'>Zmysły<'),
    (r'>Speed<', r'>Prędkość<'),
]

# Material and item properties
material_patterns = [
    (r'<h2>([^<]*) Items</h2>\n<table', r'<h2>Przedmioty z \1</h2>\n<table'),
    (r'<th>([^<]*) Items</th>', r'<th>Przedmioty z \1</th>'),
    (r'>Hardness<', r'>Twardość<'),
    (r'>HP<', r'>PŻ<'),
    (r'>BT<', r'>PU<'),
    (r'>Thin Items<', r'>Cienkie Przedmioty<'),
    (r'>Items<', r'>Przedmioty<'),
    (r'>Structure<', r'>Struktury<'),
    (r'>Low\-grade<', r'>Niskiej Jakości<'),
    (r'>Standard\-grade<', r'>Standardowej Jakości<'),
    (r'>High\-grade<', r'>Wysokiej Jakości<'),
]

# Spell-related patterns
spell_patterns = [
    (r'>Cantrip<', r'>Sztuczka<'),
    (r'>Cantrips<', r'>Sztuczki<'),
    (r'>Spell<', r'>Zaklęcie<'),
    (r'>Spells<', r'>Zaklęcia<'),
    (r'>Heightened (\(\S+\))<', r'>Wywyższenie \1<'),
    (r'>Level (\(\S+\))<', r'>Poziom \1<'),
    (r'\(At Will\)', r'(Do Woli)'),
    (r'(\S+) Innate Spells', r'Wrodzone Zaklęcia \1'),
    (r'(\S+) Prepared Spells', r'Przygotowane Zaklęcia \1'),
    (r'((Wrodzone|Przygotowane) Zaklęcia) Occult', r'\1 Okultystyczne'),
    (r'((Wrodzone|Przygotowane) Zaklęcia) Divine', r'\1 Boskie'),
    (r'((Wrodzone|Przygotowane) Zaklęcia) Primal', r'\1 Pierwotne'),
    (r'((Wrodzone|Przygotowane) Zaklęcia) Arcane', r'\1 Tajemne'),
]

# Affliction patterns (poisons, diseases)
affliction_patterns = [
    (r'>Saving Throw<', r'>Rzut Obronny<'),
    (r'>Onset<', r'>Nadejście Objawów<'),
    (r'>Stage (\d+)<', r'>Stadium \1<'),
    (r'> carrier with no ill effect', r'> Bezobjawowy nosiciel'),
    (r'\(1 day\)', r'(1 dzień)'),
    (r'\(1 round\)', r'(1 runda)'),
    (r'> (\d+) rounds<', r'> \1 rund<'),
    (r'\(Injury\)', r'(Rana)'),
    (r'\(Contact\)', r'(Dotyk)'),
    (r'\(Inhaled\)', r'(Wdychanie)'),
    (r'\(Ingested\)', r'(Spożycie)'),
]

# Action translations dictionaries
glyph_action_translations = {
    'Interact': 'Interakcja',
    'Strike': 'Cios',
    'move': 'ruch',
    'command': 'komenda',
    'envision': 'wyobrażenie',
    'manipulate': 'manipulacja',
    'concentrate': 'koncentracja',
    'emotion': 'emocjonalność',
    'fear': 'strach',
    'mental': 'mentalność',
    'visual': 'wzrokowość',
    'auditory': 'słuchowość',
    'transcendence': 'transcendencja',
    'force': 'moc',
    'spirit': 'duchowość',
    'fortune' : 'szczęście',
    'misfortune' : 'nieszczęście',
    'primal': 'magia pierwotna',
    'arcane': 'magia tajemna',
    'divine': 'magia boska',
    'occult': 'magia okultystyczna',
    'healing': 'leczenie',
    'vitality': 'witalność',
    'void': 'pustka',
    'prediction': 'przewidywanie',
    'incapacitation': 'obezwładnienie',
    'death': 'śmierć',
}

no_glyph_action_translations = {
    'Cast a Spell': 'Rzucenie Zaklęcia'
}

# Generate detailed activation patterns
detailed_activation_patterns = []

# Pattern for actions with glyphs
glyph_pattern = (
    r'<span class=\"action-glyph\">(\S+)</span> \('
    r'([^<]*?)\b{}\b([^<]*?)\)'
)

# Pattern for actions without glyphs
no_glyph_pattern = (
    r'<p><strong>Aktywacja([^<]*)</strong> '
    r'([^<]*){}([^<]*)</p>'
)

# Generate patterns for actions with glyphs
for en, pl in glyph_action_translations.items():
    detailed_activation_patterns.append((
        glyph_pattern.format(en),
        r'<span class="action-glyph">\1</span> (\2{}\3)'.format(pl)
    ))    

# Generate patterns for actions without glyphs
for en, pl in no_glyph_action_translations.items():
    detailed_activation_patterns.append((
        no_glyph_pattern.format(en),
        r'<p><strong>Aktywacja\1</strong> \2{}\3</p>'.format(pl)
    ))

# Ammunition patterns
ammunition_patterns = [
    (r'>Ammunition<', r'>Amunicja<'),
    (r'<p><strong>Amunicja</strong> ([^<]*)arrow, bolt([^<]*)</p>',
        r'<p><strong>Amunicja</strong> \1bełt, strzała\2</p>'),
    (r'<p><strong>Amunicja</strong> ([^<]*)arrow([^<]*)</p>',
        r'<p><strong>Amunicja</strong> \1strzała\2</p>'),
    (r'<p><strong>Amunicja</strong> ([^<]*)bolt([^<]*)</p>',
        r'<p><strong>Amunicja</strong> \1bełt\2</p>'),
    (r'<p><strong>Amunicja</strong> ([^<]*)any([^<]*)</p>',
        r'<p><strong>Amunicja</strong> \1dowolna\2</p>'),
]

# Frequency details
frequency_patterns = [
    (r'<p><strong>Częstotliwość</strong> once per round(\.|)</p>',
        r'<p><strong>Częstotliwość</strong> raz na rundę</p>'),
    (r'<p><strong>Częstotliwość</strong> once per day(\.|)</p>',
        r'<p><strong>Częstotliwość</strong> raz na dzień</p>'),
    (r'<p><strong>Częstotliwość</strong> once per hour(\.|)</p>',
        r'<p><strong>Częstotliwość</strong> raz na godzinę</p>'),
    (r'<p><strong>Częstotliwość</strong> once per day, plus overcharge(\.|)</p>',
        r'<p><strong>Częstotliwość</strong> raz na dzień, plus przeciążenie</p>'),
]

# Miscellaneous patterns
misc_patterns = [
    # Effect details
    (r'<p><strong>Efekt</strong> You cast (@UUID\[Compendium\.pf2e\.spells-srd\.Item\.([\w\d]*)\]\{([\p{L}\d ]*)\}).</p>',
        r'<p><strong>Efekt</strong> Rzucasz \1.</p>'),
    # Crafting
    (r'Supply a casting of the spell at the listed (rank|level)\.',
        r'Dostarcz rzucenie docelowego zaklęcia na podanym kręgu.'),
    (r'Supply a casting of a spell of the appropriate (rank|level)\.',
        r'Dostarcz rzucenie docelowego zaklęcia na odpowiednim kręgu.'),
    (r'Supply one casting of all listed levels of all listed spells\.',
        r'Dostarcz po jednym rzuceniu wszystkich wymienionych zaklęć.'),
    # Lore and setting
    (r'(\d+) AR([\W])', r'\1 RA\2'),
    # Utility text
    (r'(>|\()Note(<|\))', r'\1Przypis\2'),
]

# List conversion patterns
list_conversion_patterns = [
    # Edicts and Anathema patterns - only match if not already in <ul> format
    (r'<p><strong>(Edykty|Anatemy)</strong>\s*([^<].*?)</p>(?!\s*<ul>)', 
     lambda m: f'<p><strong>{m.group(1)}</strong></p><ul>' + 
               ''.join([f'<li>{item.strip().rstrip(".").capitalize()}</li>' 
                       for item in m.group(2).split(',') 
                       if item.strip()]) + 
               '</ul>')
]

# Combine all patterns in order of priority
replacement_patterns = (
    formatting_patterns +
    game_mechanics_patterns +
    status_conditions +
    leveled_conditions +
    item_patterns +
    religious_elements +
    activation_patterns +
    effect_patterns +
    requirement_patterns +
    usage_patterns +
    creature_patterns +
    material_patterns +
    spell_patterns +
    affliction_patterns +
    detailed_activation_patterns +
    ammunition_patterns +
    frequency_patterns +
    list_conversion_patterns +
    misc_patterns
)
