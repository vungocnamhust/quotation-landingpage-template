import { layoutRegistry, shellRegistry } from './layoutRegistry';
import { VIEW_MODES } from './contracts';
import type { ThemeDefinition } from './types';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

export function validateThemeDefinition(theme: ThemeDefinition) {
  assert(theme.supportedViewModes.length > 0, `Theme "${theme.id}" must support at least one view mode.`);

  for (const viewMode of VIEW_MODES) {
    assert(
      theme.supportedViewModes.includes(viewMode),
      `Theme "${theme.id}" must declare support for "${viewMode}".`
    );
  }

  assert(
    shellRegistry[theme.pageShell],
    `Theme "${theme.id}" references unknown page shell "${theme.pageShell}".`
  );

  assert(theme.colorRecipe, `Theme "${theme.id}" must define a color recipe.`);
  for (const scopeId of ['page', 'appChrome'] as const) {
    assert(
      theme.colorRecipe.scopes[scopeId],
      `Theme "${theme.id}" is missing color scope "${scopeId}".`
    );
  }

  for (const sectionId of theme.sectionOrder) {
    const sectionConfig = theme.sectionConfigs[sectionId];
    const typographyConfig = theme.typographyMap[sectionId];

    assert(sectionConfig, `Theme "${theme.id}" is missing section config for "${sectionId}".`);
    assert(typographyConfig, `Theme "${theme.id}" is missing typography map for "${sectionId}".`);

    for (const viewMode of theme.supportedViewModes) {
      const config = sectionConfig[viewMode];
      assert(
        config,
        `Theme "${theme.id}" section "${sectionId}" is missing config for "${viewMode}".`
      );
      assert(
        layoutRegistry[config.layoutVariant],
        `Theme "${theme.id}" section "${sectionId}" references unknown layout "${config.layoutVariant}".`
      );
      assert(
        shellRegistry[config.shellVariant],
        `Theme "${theme.id}" section "${sectionId}" references unknown shell "${config.shellVariant}".`
      );
      assert(
        theme.colorRecipe.scopes[config.colorScope],
        `Theme "${theme.id}" section "${sectionId}" references unknown color scope "${config.colorScope}".`
      );
      for (const [brandKey, brandScope] of Object.entries(config.brandColorScopes ?? {})) {
        if (!brandScope) continue;
        assert(
          theme.colorRecipe.scopes[brandScope],
          `Theme "${theme.id}" section "${sectionId}" references unknown ${brandKey} color scope "${brandScope}".`
        );
      }
      assert(
        config.colorSlots,
        `Theme "${theme.id}" section "${sectionId}" must define component color slots.`
      );

      for (const requiredViewMode of VIEW_MODES) {
        assert(
          requiredViewMode in config.visibilityByViewMode,
          `Theme "${theme.id}" section "${sectionId}" must define visibility for "${requiredViewMode}".`
        );
      }
    }
  }

  return theme;
}
