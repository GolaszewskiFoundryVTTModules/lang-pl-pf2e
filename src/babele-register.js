// Prevent errors due to data structure changes - thanks to n1xx1 from the italian localization for the coding
function removeMismatchingTypes(fallback, other = {}) {
    for (let k of Object.keys(other)) {
        const replacement = other[k];
        const replacementType = foundry.utils.getType(replacement);

        if (!fallback.hasOwnProperty(k)) {
            delete other[k];
            continue;
        }

        const original = fallback[k];
        const originalType = foundry.utils.getType(original);

        if (replacementType === "Object" && originalType === "Object") {
            removeMismatchingTypes(original, replacement);
            continue;
        }

        if (originalType !== "undefined" && replacementType !== originalType) {
            delete other[k];
        }
    }

    return fallback;
}

// Automated Animations compatibility for translated items - thanks to n1xx1 from the italian localization for the coding

function hookOnAutoAnimations() {
    if (!game.modules.has("autoanimations")) {
        return;
    }

    Hooks.on("AutomatedAnimations-WorkflowStart", (data, animationData) => {
        if (data.item?.flags?.babele?.originalName) {
            data.recheckAnimation = true;
            data.item = AACreateItemNameProxy(data.item, data.item.flags.babele.originalName);
        }

        if (data.ammoItem?.flags?.babele?.originalName) {
            data.recheckAnimation = true;
            data.ammoItem = AACreateItemNameProxy(data.ammoItem, data.ammoItem.flags.babele.originalName);
        }

        if (data.originalItem?.flags?.babele?.originalName) {
            data.recheckAnimation = true;
            data.originalItem = AACreateItemNameProxy(data.originalItem, data.originalItem.flags.babele.originalName);
        }
    });
}

function AACreateItemNameProxy(item, realName) {
    return new Proxy(item, {
        get(target, p, receiver) {
            return "name" === p ? realName : Reflect.get(target, p, receiver);
        },
    });
}

Hooks.once("babele.init", () => {
    if (game.babele) {
        game.settings.register("lang-pl-pf2e", "dual-language-names", {
            name: "Nazwy po Polsku i Angielsku",
            hint: "Oprócz nazwy polskiej używa się również nazwy angielskiej.",
            scope: "world",
            type: Boolean,
            default: false,
            config: true,
            onChange: foundry.utils.debounce(() => {
                window.location.reload();
            }, 100),
        });

        game.babele.register({
            module: "lang-pl-pf2e",
            lang: "pl",
            dir: "translation/pl/compendium",
        });

        game.babele.registerConverters({
            normalizeName: (_data, translation) => {
                return game.langPlPf2e.normalizeName(translation);
            },
            translateAdventureActorItems: (data, translation) => {
                return game.langPlPf2e.translateItems(data, translation, true, false);
            },
            translateActorDescription: (data, translation) => {
                return game.langPlPf2e.translateActorDescription(data, translation);
            },
            translateActorItems: (data, translation) => {
                return game.langPlPf2e.translateItems(data, translation, true);
            },
            translateAdventureActors: (data, translation) => {
                return game.langPlPf2e.translateArrayOfObjects(data, translation, "adventureActor");
            },
            translateAdventureItems: (data, translation) => {
                return game.langPlPf2e.translateItems(data, translation, false, false);
            },
            translateAdventureJournals: (data, translation) => {
                return game.langPlPf2e.translateArrayOfObjects(data, translation, "adventureJournal");
            },
            translateAdventureJournalPages: (data, translation) => {
                return game.langPlPf2e.translateArrayOfObjects(data, translation, "adventureJournalPage");
            },
            translateAdventureScenes: (data, translation) => {
                return game.langPlPf2e.translateArrayOfObjects(data, translation, "adventureScene");
            },
            translateDualLanguage: (data, translation) => {
                return game.langPlPf2e.translateDualLanguage(data, translation);
            },
            translateDuration: (data) => {
                return game.langPlPf2e.translateValue("duration", data);
            },
            translateHeightening: (data, translation) => {
                return game.langPlPf2e.dynamicObjectListMerge(
                    data,
                    translation,
                    game.langPlPf2e.getMapping("heightening", true)
                );
            },
            translateRange: (data) => {
                return game.langPlPf2e.translateValue("range", data);
            },
            translateRules: (data, translation) => {
                return game.langPlPf2e.translateRules(data, translation);
            },
            translateSkillSpecial: (data, translation) => {
                return game.langPlPf2e.dynamicArrayMerge(
                    data,
                    translation,
                    game.langPlPf2e.getMapping("skillSpecial", true)
                );
            },
            translateSource: (data) => {
                return game.langPlPf2e.translateValue("source", data);
            },
            translateSpellVariant: (data, translation) => {
                return game.langPlPf2e.dynamicObjectListMerge(
                    data,
                    translation,
                    game.langPlPf2e.getMapping("item", true)
                );
            },
            translateTiles: (data, translation) => {
                return game.langPlPf2e.dynamicArrayMerge(data, translation, game.langPlPf2e.getMapping("tile", true));
            },
            translateTime: (data) => {
                return game.langPlPf2e.translateValue("time", data);
            },
            translateTokens: (data, translation, _dataObject, _translatedCompendium) => {
                return game.langPlPf2e.translateArrayOfObjects(data, translation, "token");
            },
            translateTokenName: (data, translation, _dataObject, _translatedCompendium, translationObject) => {
                return game.langPlPf2e.translateTokenName(data, translation, translationObject);
            },
            updateActorImage: (data, _translations, dataObject, translatedCompendium) => {
                return game.langPlPf2e.updateImage("portrait", data, dataObject, translatedCompendium);
            },
            updateTokenImage: (data, _translations, dataObject, translatedCompendium) => {
                return game.langPlPf2e.updateImage("token", data, dataObject, translatedCompendium);
            },
        });

        hookOnAutoAnimations();
    }
});

Hooks.once("i18nInit", () => {
    if (game.i18n.lang === "pl") {
        const fallback = game.i18n._fallback;
        removeMismatchingTypes(fallback, game.i18n.translations);
    }
});
