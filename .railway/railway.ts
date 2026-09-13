import { defineRailway, postgres, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  const Postgres = postgres("Postgres", { region: "ams" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };
  const postgresVolume = volume("postgres-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "ams", sizeMB: 500 });
  const web = service("web", {
    replicas: { "ams": 1 },
  });
  const api = service("api", {
    replicas: { "ams": 1 },
    env: { APP_ENV: preserve(), ASTRAOS_DEMO_MODE: preserve(), ASTRAOS_SEED: preserve(), DATABASE_URL: preserve(), INTENT_PARSER_MODE: preserve(), PROTOCOL_ADAPTER: preserve(), RESPONSE_MODEL_MODE: preserve(), SEMANTIC_EMBEDDING_ALLOW_DOWNLOAD: preserve(), SEMANTIC_EMBEDDING_PROVIDER: preserve() },
  });

  return project("astraos", {
    resources: [web, api, Postgres, postgresVolume],
  });
});
