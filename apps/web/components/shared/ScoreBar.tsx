import { AstraScore } from "@/components/astra";

export function ScoreBar({
  value,
  label,
  large = false,
  display,
  suffix,
}: {
  value: number;
  label?: string;
  large?: boolean;
  display?: string;
  suffix?: string;
}) {
  return (
    <AstraScore
      value={value}
      label={label}
      display={display}
      suffix={suffix ?? "/ 100"}
      size={large ? "large" : "default"}
    />
  );
}
