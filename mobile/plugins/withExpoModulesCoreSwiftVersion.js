const { withDangerousMod } = require('@expo/config-plugins');
const fs = require('fs');
const path = require('path');

const MARKER = '# [calendar-ai] ExpoModulesCore Swift 5';

const SNIPPET = `
    ${MARKER}
    installer.pods_project.targets.each do |target|
      next unless target.name == 'ExpoModulesCore'
      target.build_configurations.each do |cfg|
        cfg.build_settings['SWIFT_VERSION'] = '5.0'
      end
    end`;

/**
 * Keeps ExpoModulesCore on Swift 5 language mode (see patches/expo-modules-core+*.patch).
 * Safe to run after every prebuild; idempotent.
 */
module.exports = function withExpoModulesCoreSwiftVersion(config) {
  return withDangerousMod(config, [
    'ios',
    (config) => {
      const podfilePath = path.join(config.modRequest.platformProjectRoot, 'Podfile');
      if (!fs.existsSync(podfilePath)) {
        return config;
      }
      let podfile = fs.readFileSync(podfilePath, 'utf8');
      if (podfile.includes(MARKER)) {
        return config;
      }

      const anchor = /react_native_post_install\([\s\S]*?\n    \)/;
      const match = podfile.match(anchor);
      if (!match) {
        return config;
      }
      const insertAt = match.index + match[0].length;
      podfile = podfile.slice(0, insertAt) + SNIPPET + podfile.slice(insertAt);
      fs.writeFileSync(podfilePath, podfile);
      return config;
    },
  ]);
};
