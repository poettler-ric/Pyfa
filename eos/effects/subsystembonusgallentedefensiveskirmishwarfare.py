# subSystemBonusGallenteDefensiveSkirmishWarfare
#
# Used by:
# Subsystem: Proteus Defensive - Warfare Processor
type = "passive"
def handler(fit, module, context):
    level = fit.character.getSkill("Gallente Defensive Systems").level
    fit.modules.filteredItemBoost(lambda mod: mod.item.requiresSkill("Skirmish Warfare Specialist"),
                                  "commandBonus", module.getModifiedItemAttr("subsystemBonusGallenteDefensive") * level)
