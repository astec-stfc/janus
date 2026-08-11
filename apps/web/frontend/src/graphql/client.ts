import { GraphQLClient } from "graphql-request";

const graphqlEndpoint =
  import.meta.env.VITE_GRAPHQL_URL ??
  new URL("/graphql", window.location.href).toString();

export const graphqlClient = new GraphQLClient(graphqlEndpoint);
