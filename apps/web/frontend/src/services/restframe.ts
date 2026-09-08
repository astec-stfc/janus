import axios from "axios";
import type { PhysicalElement } from "../types";

interface PhysicalElementsResponse {
  facility: string;
  layout: string;
  elements: PhysicalElement[];
}

interface ElementTypesResponse {
  facility: string;
  total: number;
  type_counts: Record<string, number>;
}

const baseUrl = "/restframe";

const getAvailableElementTypes = async (): Promise<string[]> => {
  const response = await axios.get<ElementTypesResponse>(
    `${baseUrl}/diagnostics/physical-element-types`
  );

  return Object.keys(response.data.type_counts);
};

const getPhysicalElements = async (
  include: readonly string[] = [],
): Promise<PhysicalElement[]> => {
  const params = new URLSearchParams();
  for (const elementType of include) params.append("include", elementType);

  const response = await axios.get<PhysicalElementsResponse>(
    `${baseUrl}/diagnostics/physical-elements`,
    { params },
  );
  return response.data.elements;
};

export default { getPhysicalElements, getAvailableElementTypes };
