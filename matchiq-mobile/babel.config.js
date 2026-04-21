// Configurazione Babel per Expo (richiesta da expo-router)
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
  };
};
