import axios from "axios";
import type {
  Beam,
  BeamSummary,
  BeamSummaryParameter,
  LatticeResponse,
  TwissPlotResponse,
} from "../types";

const baseUrl = "/v1";
const latticeBase = `${baseUrl}/lattice`;

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

const getScreenBeam = async (uuid: string, name: string): Promise<Beam> => {
  const response = await axios.get<Beam>(`${latticeBase}/screen/beam/`, {
    params: { uuid, name },
  });
  return response.data;
};

const getLattice = async (uuid: string): Promise<LatticeResponse> => {
  const response = await axios.get<LatticeResponse>(`${latticeBase}/`, {
    params: { uuid },
  });
  return response.data;
};

const getLatticeforTwissPlot = async (
  uuid: string,
): Promise<TwissPlotResponse> => {
  const lattice = await getLattice(uuid);
  const beamSummary = lattice.beam_summary;

  if (!beamSummary) {
    return {
      uuid: lattice.uuid,
      facility: lattice.facility,
      beamSummaryData: null,
    };
  }

  const yParameters: BeamSummaryParameter[] = [];
  for (const beamSummaryName of Object.keys(
    beamSummary,
  ) as (keyof BeamSummary)[]) {
    const values = beamSummary[beamSummaryName];
    if (beamSummaryName !== "position" && Array.isArray(values)) {
      yParameters.push({
        name: beamSummaryName,
        label: beamSummaryName,
        values,
      });
    }
  }

  return {
    uuid: lattice.uuid,
    facility: lattice.facility,
    beamSummaryData: {
      xParameter: {
        name: "position",
        label: "Position",
        unit: "m",
        values: beamSummary.position,
      },
      yParameters,
    },
  };
};

export default {
  getRunUuids,
  getScreenNames,
  getScreenBeam,
  getLattice,
  getLatticeforTwissPlot,
};
