// Przycisk "Odśwież aktora" pozwala na pobranie tłumaczeń aktorów na scenie bądź zaimportowanych
async function injectHeaderTranslationButtonActor(sheet, buttons)
{
    // Early return for character or party type actors
    if (sheet.actor && (sheet.actor.type === "character" || sheet.actor.type === "party")) return;

    const document = sheet.item ?? sheet.object;
    if (!(document instanceof foundry.abstract.Document)) throw new Error('Could not locate sheet\'s document');

    // Definiowanie przycisku "Odśwież aktora"
    const refreshButton = {
        class: 'refresh-actor',
        icon: 'fas fa-sync',
        label: "Odśwież aktora",
        onclick: () => refreshActor(sheet.actor.id),
    };

    // Insert refresh button before close button or at the end
    const closeIndex = buttons.findIndex(button => button.class.includes('close'));
    closeIndex !== -1 
        ? buttons.splice(closeIndex, 0, refreshButton)
        : buttons.push(refreshButton);
}

Hooks.on("getActorSheetHeaderButtons", injectHeaderTranslationButtonActor);

// Funkcja tłumaczenia aktora
async function refreshActor(actorId)
{
    try
    {
        const actor = game.actors.get(actorId);
        if (!actor)
        {
            ui.notifications.error(`Nie znaleziono aktora o ID ${actorId}.`);
            return;
        }

        if(!game.actors.get(actor.id))
        {
            ui.notifications.error(`Aktor nie może być zaktualizowany, ponieważ nie istnieje.`);
            return;
        }

        const sourceId = actor._source._stats?.compendiumSource;
        if (!sourceId)
        {
            ui.notifications.error(`Aktor nie pochodzi z kompendium.`);
            return;
        }

        const [, systemName, compendiumName, , entryId] = sourceId.split(".");
        const pack = game.packs.get(`${systemName}.${compendiumName}`);
        
        if (!pack)
        {
            ui.notifications.error(`Nie znaleziono kompendium dla tego aktora.`);
            return;
        }

        const entry = await pack.getDocument(entryId);
        if (!entry)
        {
            ui.notifications.error(`Nie można pobrać danych aktora z kompendium.`);
            return;
        }

        // Prepare update data while preserving existing folder
        const updateData = entry.toObject();
        updateData.folder = actor.folder?.id || null;
        delete updateData.img;  // Do not update the portrait
        delete updateData.token; // Do not update the token
        
        // Update token name in prototype and on scene
        await updateTokenName(actor, entry.name);

        await actor.update(updateData);
        
        // Update actor's spells
        await updateActorSpells(actor);

        ui.notifications.info(`Aktor ${actor.name} został odświeżony z kompendium.`);
    }
    catch (error)
    {
        console.error(error);
        ui.notifications.error("Wystąpił błąd podczas odświeżania aktora.");
    }
}

// Extract token name update logic
async function updateTokenName(actor, newName)
{
    // Update prototype token name
    await actor.prototypeToken.update({ name: newName });

    // Update tokens on scene
    const sceneTokens = canvas.tokens.placeables.filter(t => t.actor?.id === actor.id);
    for (let token of sceneTokens)
    {
        await token.document.update({ name: newName });
    }
}

// Extract spell update logic
async function updateActorSpells(actor)
{
    for (const spell of actor.items.filter(item => item.type === "spell"))
    {
        const spellCompendiumSource = spell._source._stats?.compendiumSource;
        if (!spellCompendiumSource) continue;

        const [, spellSystem, spellCompendium, , spellEntryId] = spellCompendiumSource.split(".");
        const spellPack = game.packs.get(`${spellSystem}.${spellCompendium}`);

        if (!spellPack)
        {
            console.warn(`Nie znaleziono kompendium dla zaklęcia ${spell.name}: ${spellSystem}.${spellCompendium}`);
            continue;
        }

        // Ensure pack index is loaded
        if (!spellPack.index.size)
        {
            await spellPack.getIndex();
        }

        const spellEntry = await spellPack.getDocument(spellEntryId);

        if (spellEntry && (spell.name !== spellEntry.name || spell.system.description.value !== spellEntry.system.description.value))
        {
            await spell.update({
                name: spellEntry.name,
                "system.description.value": spellEntry.system.description.value
            });
        }
    }
}