import axios from "axios";
import type { Beam, LatticeResponse } from "../types";

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

export default { getRunUuids, getScreenNames, getScreenBeam, getLattice };
