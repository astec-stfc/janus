import axios from "axios";
import type { PhysicalElement } from "../types";

interface PhysicalElementsResponse {
  facility: string;
  layout: string;
  elements: PhysicalElement[];
}

const baseUrl = "/restframe";

const getPhysicalElements = async (
  layout: string,
  include: readonly string[] = [],
): Promise<PhysicalElement[]> => {
  const params = new URLSearchParams();
  params.set("layout", layout);
  for (const elementType of include) params.append("include", elementType);

  const response = await axios.get<PhysicalElementsResponse>(
    `${baseUrl}/diagnostics/physical-elements`,
    { params },
  );
  return response.data.elements;
};

export default { getPhysicalElements };
