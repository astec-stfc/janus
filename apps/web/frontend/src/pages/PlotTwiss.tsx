import TwissPlotAreaContent from "@/components/plot/TwissPlotAreaContent";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useTwissData } from "@/hooks/useTwissData";
import type { FormEvent } from "react";
import { useState } from "react";

const PlotTwiss = () => {
  const [uuidInput, setUuidInput] = useState("");
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null);

  const twissData = useTwissData(selectedUuid);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSelectedUuid(uuidInput.trim() || null);
  };

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
        <TwissPlotAreaContent {...twissData} />
      </div>
    </div>
  );
};

export default PlotTwiss;
