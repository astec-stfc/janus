import { graphqlClient } from "../graphql/client";
import {
  GetBeamSummaryDocument,
  GetMarkerNamesDocument,
  GetRunsDocument,
  GetScreenNamesDocument,
  GetRunUuidsDocument,
} from "../graphql/generated/graphql";
import type {
  BeamSummary,
  BeamSummaryPlotResponse,
  DomainPathTuple,
  HSDSDatasetPath,
  RunSummary,
} from "../types";
import { fetchVectorDatasetBatch } from "./hsds.rest";

const getRunUuids = async (): Promise<string[]> => {
  const data = await graphqlClient.request(GetRunUuidsDocument);
  return data.getRunUuids;
};

const getRuns = async (): Promise<RunSummary[]> => {
  const data = await graphqlClient.request(GetRunsDocument);

  return data.getRuns.map((run) => ({
    uuid: run.uuid,
    facility: run.facility,
    timestamp: run.timestamp,
    client_id: run.clientId,
    success: run.success,
  }));
};

const getScreenNames = async (uuid: string): Promise<string[]> => {
  const data = await graphqlClient.request(GetScreenNamesDocument, { uuid });
  return data.getScreenNames;
};

const getMarkerNames = async (uuid: string): Promise<string[]> => {
  const data = await graphqlClient.request(GetMarkerNamesDocument, { uuid });
  return data.getMarkerNames;
};

const getBeamSummary = async (
  uuid: string,
): Promise<BeamSummaryPlotResponse> => {
  const data = await graphqlClient.request(GetBeamSummaryDocument, { uuid });
  const result = data.getBeamSummary;

  if (!result) {
    return { uuid, facility: "", beamSummaryData: null };
  }

  if (!result.beamSummaryData) {
    return {
      uuid: result.uuid,
      facility: result.facility,
      beamSummaryData: null,
    };
  }

  const { xParameter, yParameters } = result.beamSummaryData;
  const datasetPaths: HSDSDatasetPath = Object.fromEntries(
    [xParameter, ...yParameters].map(({ name, domainPathTuple }) => [
      name,
      domainPathTuple as DomainPathTuple,
    ]),
  );
  const datasets = await fetchVectorDatasetBatch(datasetPaths);

  return {
    uuid: result.uuid,
    facility: result.facility,
    beamSummaryData: {
      xParameter: {
        name: xParameter.name as keyof BeamSummary,
        label: xParameter.label,
        unit: xParameter.unit ?? undefined,
        values: datasets[xParameter.name],
      },
      yParameters: yParameters.map((parameter) => ({
        name: parameter.name as keyof BeamSummary,
        label: parameter.label,
        values: datasets[parameter.name],
      })),
    },
  };
};

export default {
  getRunUuids,
  getRuns,
  getScreenNames,
  getMarkerNames,
  getBeamSummary,
};
