import TwissPlot from "@/components/plot/TwissPlot";
import type { TwissPlotData } from "@/lib/twissPlot";

interface TwissPlotAreaContentProps {
  plotData: TwissPlotData | null;
  loading: boolean;
  errorMessage: string | null;
  emptyText: string;
}

const CenteredMessage = ({ text }: { text: string }) => (
  <div className="flex h-full items-center justify-center">
    <p className="text-sm text-muted-foreground">{text}</p>
  </div>
);

const TwissPlotAreaContent = ({
  plotData,
  loading,
  errorMessage,
  emptyText,
}: TwissPlotAreaContentProps) => {
  if (loading) return <CenteredMessage text="Loading Twiss plot..." />;
  if (errorMessage) return <CenteredMessage text={errorMessage} />;
  if (!plotData) return <CenteredMessage text={emptyText} />;

  return (
    <TwissPlot
      beamSummaryData={plotData.beamSummaryData}
      elements={plotData.elements}
    />
  );
};

export default TwissPlotAreaContent;
