import { graphqlClient } from "../graphql/client";
import {
  GetBeamSummaryDocument,
  GetMarkerNamesDocument,
  GetRunsDocument,
  GetScreenNamesDocument,
  GetRunUuidsDocument,
} from "../graphql/generated/graphql";
import type { BeamSummary, BeamSummaryPlotResponse, RunSummary } from "../types";

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

  return {
    uuid: result.uuid,
    facility: result.facility,
    beamSummaryData: {
      xParameter: {
        name: result.beamSummaryData.xParameter.name as keyof BeamSummary,
        label: result.beamSummaryData.xParameter.label,
        unit: result.beamSummaryData.xParameter.unit ?? undefined,
        values: result.beamSummaryData.xParameter.values,
      },
      yParameters: result.beamSummaryData.yParameters.map((p) => ({
        name: p.name as keyof BeamSummary,
        label: p.label,
        values: p.values,
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
