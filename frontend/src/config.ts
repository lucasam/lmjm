interface AppConfig {
  cognitoDomain: string;
  cognitoClientId: string;
  redirectUri: string;
  apiUrl: string;
}

let _config: AppConfig | null = null;

export async function loadConfig(): Promise<AppConfig> {
  if (_config) return _config;
  const response = await fetch('/config.json');
  if (!response.ok) {
    throw new Error('Failed to load config.json');
  }
  _config = (await response.json()) as AppConfig;
  return _config;
}

export function getConfig(): AppConfig {
  if (!_config) {
    throw new Error('Config not loaded. Call loadConfig() first.');
  }
  return _config;
}
