import type { CodegenConfig } from "@graphql-codegen/cli";

const latticeApiUrl = process.env.LATTICE_API_URL ?? "http://localhost:1337";
const schemaUrl = process.env.GRAPHQL_SCHEMA_URL ?? `${latticeApiUrl}/graphql`;

const config: CodegenConfig = {
  schema: schemaUrl,
  documents: "src/graphql/operations/**/*.graphql",
  generates: {
    "src/graphql/generated/": {
      preset: "client",
      config: {
        useTypeImports: true,
      },
    },
  },
};

export default config;
