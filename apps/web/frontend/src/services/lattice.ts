import axios from "axios";
import type {
  Beam,
  BeamSummary,
  BeamSummaryParameter,
  BeamSummaryPlotResponse,
  LatticeResponse,
} from "../types";

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
const BEAM_ARRAY_FIELDS: (keyof Beam)[] = ["x", "y", "z", "cpx", "cpy", "cpz"];
const NULL_ARRAY_SENTINEL = 0xffffffff;

const decodeBeamBinary = (buffer: ArrayBuffer): Beam => {
  const view = new DataView(buffer);
  if (buffer.byteLength < 4) {
    throw new Error("Invalid beam binary payload: too small");
  }

  const magic = String.fromCharCode(
    view.getUint8(0),
    view.getUint8(1),
    view.getUint8(2),
    view.getUint8(3),
  );
  if (magic !== "JBM1") {
    throw new Error(`Unsupported beam binary format: ${magic}`);
  }

  let offset = 4;
  const beam: Beam = {
    x: null,
    y: null,
    z: null,
    cpx: null,
    cpy: null,
    cpz: null,
  };

  for (const field of BEAM_ARRAY_FIELDS) {
    if (offset + 4 > buffer.byteLength) {
      throw new Error("Invalid beam binary payload: truncated field header");
    }
    const count = view.getUint32(offset, true);
    offset += 4;

    if (count === NULL_ARRAY_SENTINEL) {
      beam[field] = null;
      continue;
    }

    const bytes = count * 4;
    if (offset + bytes > buffer.byteLength) {
      throw new Error("Invalid beam binary payload: truncated field data");
    }

    // Create a copy to avoid exposing a view onto the transport buffer.
    const values = new Float32Array(buffer, offset, count);
    beam[field] = Array.from(values);
    offset += bytes;
  }

  return beam;
};

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

const getScreenBeam = async (uuid: string, name: string): Promise<Beam> => {
  try {
    const response = await axios.get<ArrayBuffer>(`${latticeBase}/screen/beam/binary/`, {
      params: { uuid, name },
      responseType: "arraybuffer",
    });
    return decodeBeamBinary(response.data);
  } catch (_error) {
    // Fallback keeps compatibility with older servers without the binary route.
  }

  const response = await axios.get<Beam>(`${latticeBase}/screen/beam/`, {
    params: { uuid, name },
  });
  return response.data;
};

const getMarkerBeam = async (uuid: string, name: string): Promise<Beam> => {
  try {
    const response = await axios.get<ArrayBuffer>(`${latticeBase}/marker/beam/binary/`, {
      params: { uuid, name },
      responseType: "arraybuffer",
    });
    return decodeBeamBinary(response.data);
  } catch (_error) {
    // Fallback keeps compatibility with older servers without the binary route.
  }

  const response = await axios.get<Beam>(`${latticeBase}/marker/beam/`, {
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
): Promise<BeamSummaryPlotResponse> => {
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
  getMarkerNames,
  getScreenBeam,
  getMarkerBeam,
  getLattice,
  getLatticeforTwissPlot,
};
