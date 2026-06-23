import TwissPlot from "@/components/plot/TwissPlot";
import { PLOTTED_ELEMENT_TYPES } from "@/components/plot/TwissPlotElements";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import latticeService from "@/services/lattice";
import restframeService from "@/services/restframe";
import type {
  BeamSummaryData,
  BeamSummaryPlotResponse,
  PhysicalElement,
} from "@/types";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

const hasBeamSummaryData = (
  beamSummaryData: BeamSummaryData | null | undefined,
): beamSummaryData is BeamSummaryData => {
  if (!beamSummaryData) return false;
  const length = beamSummaryData.xParameter.values.length;
  return (
    length > 0 &&
    beamSummaryData.yParameters.every(
      (parameter) => parameter.values.length === length,
    )
  );
};

const PlotTwiss = () => {
  const [uuidInput, setUuidInput] = useState("");
  const [plotLattice, setPlotLattice] =
    useState<BeamSummaryPlotResponse | null>(null);
  const [elements, setElements] = useState<PhysicalElement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPlot = useCallback(async (uuid: string) => {
    setLoading(true);
    setError(null);

    try {
      const [nextLattice, nextElements] = await Promise.all([
        latticeService.getLatticeforTwissPlot(uuid),
        restframeService.getPhysicalElements(PLOTTED_ELEMENT_TYPES),
      ]);
      setPlotLattice(nextLattice);
      setElements(nextElements);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unable to load plot.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPlot("");
  }, [loadPlot]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void loadPlot(uuidInput.trim());
  };

  const beamSummaryData = plotLattice?.beamSummaryData;
  const canPlot = hasBeamSummaryData(beamSummaryData) && !loading && !error;

  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <form className="flex gap-2" onSubmit={handleSubmit}>
        <Input
          value={uuidInput}
          onChange={(event) => setUuidInput(event.target.value)}
          placeholder="UUID"
        />
        <Button type="submit">Plot</Button>
      </form>

      <div className="min-h-0 flex-1 rounded-lg border p-3">
        {loading && <div>Loading...</div>}
        {!loading && error && <div>{error}</div>}
        {!loading && !error && !hasBeamSummaryData(beamSummaryData) && (
          <div>No data.</div>
        )}
        {canPlot && (
          <TwissPlot beamSummaryData={beamSummaryData} elements={elements} />
        )}
      </div>
    </div>
  );
};

export default PlotTwiss;
