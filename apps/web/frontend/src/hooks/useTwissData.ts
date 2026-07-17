import { getErrorMessage } from "@/lib/utils";
import {
  PLOTTED_TWISS_PARAMETER_NAMES,
  type TwissPlotData,
} from "@/lib/twissPlot";
import { useBeamSummaryQuery } from "@/queries/lattice.queries";
import { usePhysicalElementsQuery } from "@/queries/restframe.queries";
import type { BeamSummaryData } from "@/types";

const hasPlottableBeamSummaryData = (
  beamSummaryData: BeamSummaryData | null,
): beamSummaryData is BeamSummaryData => {
  if (!beamSummaryData) return false;

  const length = beamSummaryData.xParameter.values.length;
  if (length === 0) return false;

  const plottedParameters = beamSummaryData.yParameters.filter((parameter) =>
    PLOTTED_TWISS_PARAMETER_NAMES.includes(parameter.name),
  );

  return (
    plottedParameters.length > 0 &&
    plottedParameters.every(
      (parameter) => parameter.values.length === length,
    )
  );
};

export function useTwissData(uuid: string | null) {
  const beamSummaryQuery = useBeamSummaryQuery(uuid);
  const physicalElementsQuery = usePhysicalElementsQuery({
    enabled: Boolean(uuid),
  });

  const beamSummaryData = beamSummaryQuery.data?.beamSummaryData ?? null;
  const elements = physicalElementsQuery.data ?? [];
  const loading = beamSummaryQuery.isLoading || physicalElementsQuery.isLoading;

  const error = beamSummaryQuery.error ?? physicalElementsQuery.error;
  const errorMessage = error
    ? getErrorMessage(error, "Unable to load plot.")
    : null;
  const plotData: TwissPlotData | null = hasPlottableBeamSummaryData(
    beamSummaryData,
  )
    ? { beamSummaryData, elements }
    : null;
  const emptyText = uuid
    ? "No Twiss data available for the selected run."
    : "Enter a UUID to view Twiss plots.";

  return { plotData, loading, errorMessage, emptyText };
}
