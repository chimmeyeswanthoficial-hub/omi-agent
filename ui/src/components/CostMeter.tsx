import { fmtNum } from "../lib/format";

export default function CostMeter({ tokensIn, tokensOut, usd }: { tokensIn: number; tokensOut: number; usd: number }) {
  return (
    <span className="text-[10px] text-mut ml-auto" title="tokens + provider cost for this call">
      {fmtNum(tokensIn)}↑ {fmtNum(tokensOut)}↓ · ${usd.toFixed(4)}
    </span>
  );
}
