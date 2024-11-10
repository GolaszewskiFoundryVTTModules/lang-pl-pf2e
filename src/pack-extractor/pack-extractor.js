import { readFileSync, writeFileSync } from "fs";
import { getZipContentFromURL, writeFilesFromBlob } from "../helper/src/util/file-handler.js";
import { replaceProperties } from "../helper/src/util/utilities.js";
import { buildItemDatabase, extractPackGroupList } from "../helper/src/pack-extractor/pack-extractor.js";
import { PF2_DEFAULT_MAPPING } from "../helper/src/pack-extractor/constants.js";

// Read config file
const configFile = JSON.parse(readFileSync("./src/pack-extractor/pack-extractor-config.json", "utf-8"));

const CONFIG = { ...configFile, mappings: PF2_DEFAULT_MAPPING };

// Replace linked mappings and savePaths with actual data
replaceProperties(CONFIG.mappings, ["subMapping"], CONFIG.mappings);
replaceProperties(CONFIG.packs, ["mapping"], CONFIG.mappings);
replaceProperties(CONFIG.packs, ["savePath"], CONFIG.filePaths.packs);

// Fetch assets from current pf2 release and get zip contents
const packs = await getZipContentFromURL(CONFIG.filePaths.zipURL);

// Build item database in order to compare actor items with their compendium entries
const itemDatabase = buildItemDatabase(packs, CONFIG.itemDatabase);

// Extract data for all configured packs
const extractedPackGroupList = extractPackGroupList(packs, CONFIG.packs, itemDatabase);

// Write extracted packs to target directories
Object.keys(extractedPackGroupList.extractedPackGroups).forEach((packGroup) => {
    const path = CONFIG.packs[packGroup].savePath;
    Object.keys(extractedPackGroupList.extractedPackGroups[packGroup]).forEach((pack) => {
        writeFileSync(
            `${path}/${pack}.json`,
            JSON.stringify(extractedPackGroupList.extractedPackGroups[packGroup][pack], null, 2)
        );
    });
});

// Write dictionary to target directory
writeFileSync(CONFIG.filePaths.dictionary, JSON.stringify(extractedPackGroupList.packGroupListDictionary, null, 2));

// Extract and write i18n files
writeFilesFromBlob(
    packs.filter((pack) => CONFIG.i18nFiles.includes(`${pack.fileName}.${pack.fileType}`)),
    CONFIG.filePaths.i18n,
    "i8n files"
);

// Check for unconfigured files
const configuredPacks = new Set(
    Object.values(CONFIG.packs)
        .flatMap(group => group.packNames)
        .map(name => `${name}.json`)
);

// Remove .json extension from configured i18n files
const configuredI18n = new Set(CONFIG.i18nFiles.map(file => file.replace('.json', '')));

const unconfiguredFiles = packs
    .filter(pack => pack.fileType === 'json')
    .filter(pack => {
        // Skip _folders files
        if (pack.fileName.endsWith('_folders')) return false;
        // Skip i18n files that are properly configured
        if (configuredI18n.has(pack.fileName)) return false;
        // Check if pack files are configured
        return !configuredPacks.has(`${pack.fileName}.${pack.fileType}`);
    })
    .map(pack => pack.fileName + '.' + pack.fileType);

if (unconfiguredFiles.length > 0) {
    console.warn('\x1b[33m%s\x1b[0m', 'Warning: The following files from the zip are not configured in pack-extractor-config.json:');
    unconfiguredFiles.forEach(file => console.warn('\x1b[33m%s\x1b[0m', `- ${file}`));
}
