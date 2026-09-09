import axios from "axios";
import type { Beam, BeamDatasetPath } from "../types";

import { fetchVectorDatasetBatch } from "./hsds.rest";

export type BeamKind = "screen" | "marker";

interface LatticeBinaryMetadataResponse {
  lattice_template?: {
    sections?: Record<
      string,
      {
        markers?: { name: string }[] | null;
      }
    >;
  } | null;
}

const baseUrl = "/v1/";
const latticeBase = `${baseUrl}lattice`;

const getRunUuids = async (): Promise<string[]> => {
  const response = await axios.get<string[]>(`${latticeBase}/runs`);
  return response.data;
};

const getScreenNames = async (uuid: string): Promise<string[]> => {
  const response = await axios.get<string[]>(`${latticeBase}/screens/names/`, {
    params: { uuid },
  });
  return response.data;
};

const getMarkerNames = async (uuid: string): Promise<string[]> => {
  const response = await axios.get<LatticeBinaryMetadataResponse>(
    `${latticeBase}/binary/metadata`,
    {
      params: { uuid },
    },
  );

  const sections = response.data.lattice_template?.sections ?? {};
  const markerNames = Object.values(sections).flatMap((section) =>
    (section.markers ?? []).map((marker) => marker.name),
  );

  if (markerNames.length > 0) {
    return markerNames;
  }

  const fallbackResponse = await axios.get<string[]>(
    `${latticeBase}/markers/names/`,
    {
      params: { uuid },
    },
  );
  return fallbackResponse.data;
};

const getBeam = async (
  uuid: string,
  name: string,
  kind: BeamKind,
): Promise<Beam> => {
  const response = await axios.get<BeamDatasetPath>(
    `${latticeBase}/${kind}/beam/`,
    { params: { uuid, name } },
  );

  return await fetchVectorDatasetBatch(response.data);
};

export default {
  getRunUuids,
  getScreenNames,
  getMarkerNames,
  getBeam,
};
