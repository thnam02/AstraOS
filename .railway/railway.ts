import { defineRailway, github, postgres, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  const Postgres = postgres("Postgres", { region: "ams" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };
  const postgresVolumeAD_L = volume("postgres-volume-aD_L", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "ams", sizeMB: 500 });
  const web = service("web", {
    source: github("thnam02/AstraOS", { branch: "nam/dev", checkSuites: false, rootDirectory: "/apps/web" }),
    build: { buildEnvironment: "V3", builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    replicas: { "ams": 1 },
    env: { NEXT_PUBLIC_API_URL: preserve() },
  });
  const api = service("api", {
    source: github("thnam02/AstraOS", { branch: "nam/dev", checkSuites: false, rootDirectory: "/apps/api" }),
    build: { buildEnvironment: "V3", builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    replicas: { "ams": 1 },
    env: { APP_ENV: preserve(), ASTRAOS_DEMO_MODE: preserve(), ASTRAOS_SEED: preserve(), DATABASE_URL: preserve(), FRONTEND_URL: preserve(), INTENT_PARSER_MODE: preserve(), PROTOCOL_ADAPTER: preserve(), RESPONSE_MODEL_MODE: preserve(), SEMANTIC_EMBEDDING_ALLOW_DOWNLOAD: preserve(), SEMANTIC_EMBEDDING_PROVIDER: preserve() },
  });

  return project("astraos", {
    resources: [web, api, Postgres, postgresVolumeAD_L],
  });
});
