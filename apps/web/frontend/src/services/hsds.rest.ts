import axios from "axios";
import { toByteArray } from "base64-js";
import type { HSDSDataset, HSDSDatasetPath } from "../types";

const hsdsBase = "/hsds";
const datasetBase = `${hsdsBase}/dataset/`;
const datasetValueBase = `${datasetBase}values/`;
const datasetBatchBase = `${datasetValueBase}batch`;

export const fetchVectorDataset = async (
  domain: string,
  path: string,
): Promise<ArrayBuffer> => {
  const response = await axios.get<ArrayBuffer>(`${datasetValueBase}`, {
    params: { domain, path },
    responseType: "arraybuffer",
  });
  return response.data;
};

export const fetchScalarDataset = async (
  domain: string,
  path: string,
): Promise<number> => {
  const response = await axios.get<number>(`${datasetValueBase}`, {
    params: { domain, path },
  });
  return response.data;
};

const decodeBase64ToNumbers = (base64: string): number[] =>
  Array.from(new Float64Array(toByteArray(base64).buffer));

export const fetchVectorDatasetBatch = async <
  DatasetPaths extends HSDSDatasetPath,
>(
  datasetPaths: DatasetPaths,
): Promise<HSDSDataset<DatasetPaths>> => {
  const response = await axios.post<HSDSDataset<DatasetPaths, string>>(
    datasetBatchBase,
    { requests: datasetPaths },
    { headers: { "Content-Type": "application/json" } },
  );

  return Object.fromEntries(
    Object.entries(response.data).map(([name, data]) => [
      name,
      decodeBase64ToNumbers(data),
    ]),
  ) as HSDSDataset<DatasetPaths>;
};

export default {
  fetchVectorDataset,
  fetchScalarDataset,
  fetchVectorDatasetBatch,
};
