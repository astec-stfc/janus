/* eslint-disable */
import * as types from './graphql';
import type { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';

/**
 * Map of all GraphQL operations in the project.
 *
 * This map has several performance disadvantages:
 * 1. It is not tree-shakeable, so it will include all operations in the project.
 * 2. It is not minifiable, so the string of a GraphQL query will be multiple times inside the bundle.
 * 3. It does not support dead code elimination, so it will add unused operations.
 *
 * Therefore it is highly recommended to use the babel or swc plugin for production.
 * Learn more about it here: https://the-guild.dev/graphql/codegen/plugins/presets/preset-client#reducing-bundle-size
 */
type Documents = {
    "query GetRunUuids {\n  getRunUuids\n}\n\nquery GetScreenNames($uuid: String!) {\n  getScreenNames(uuid: $uuid)\n}\n\nquery GetMarkerNames($uuid: String!) {\n  getMarkerNames(uuid: $uuid)\n}\n\nquery GetBeamSummary($uuid: String!) {\n  getBeamSummary(uuid: $uuid) {\n    uuid\n    facility\n    beamSummaryData {\n      xParameter {\n        name\n        label\n        unit\n        values\n      }\n      yParameters {\n        name\n        label\n        values\n      }\n    }\n  }\n}": typeof types.GetRunUuidsDocument,
};
const documents: Documents = {
    "query GetRunUuids {\n  getRunUuids\n}\n\nquery GetScreenNames($uuid: String!) {\n  getScreenNames(uuid: $uuid)\n}\n\nquery GetMarkerNames($uuid: String!) {\n  getMarkerNames(uuid: $uuid)\n}\n\nquery GetBeamSummary($uuid: String!) {\n  getBeamSummary(uuid: $uuid) {\n    uuid\n    facility\n    beamSummaryData {\n      xParameter {\n        name\n        label\n        unit\n        values\n      }\n      yParameters {\n        name\n        label\n        values\n      }\n    }\n  }\n}": types.GetRunUuidsDocument,
};

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 *
 *
 * @example
 * ```ts
 * const query = graphql(`query GetUser($id: ID!) { user(id: $id) { name } }`);
 * ```
 *
 * The query argument is unknown!
 * Please regenerate the types.
 */
export function graphql(source: string): unknown;

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(source: "query GetRunUuids {\n  getRunUuids\n}\n\nquery GetScreenNames($uuid: String!) {\n  getScreenNames(uuid: $uuid)\n}\n\nquery GetMarkerNames($uuid: String!) {\n  getMarkerNames(uuid: $uuid)\n}\n\nquery GetBeamSummary($uuid: String!) {\n  getBeamSummary(uuid: $uuid) {\n    uuid\n    facility\n    beamSummaryData {\n      xParameter {\n        name\n        label\n        unit\n        values\n      }\n      yParameters {\n        name\n        label\n        values\n      }\n    }\n  }\n}"): (typeof documents)["query GetRunUuids {\n  getRunUuids\n}\n\nquery GetScreenNames($uuid: String!) {\n  getScreenNames(uuid: $uuid)\n}\n\nquery GetMarkerNames($uuid: String!) {\n  getMarkerNames(uuid: $uuid)\n}\n\nquery GetBeamSummary($uuid: String!) {\n  getBeamSummary(uuid: $uuid) {\n    uuid\n    facility\n    beamSummaryData {\n      xParameter {\n        name\n        label\n        unit\n        values\n      }\n      yParameters {\n        name\n        label\n        values\n      }\n    }\n  }\n}"];

export function graphql(source: string) {
  return (documents as any)[source] ?? {};
}

export type DocumentType<TDocumentNode extends DocumentNode<any, any>> = TDocumentNode extends DocumentNode<  infer TType,  any>  ? TType  : never;