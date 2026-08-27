import type { ShortlistItem, TradeEvent } from "../types";

export function latestShortlist(events: TradeEvent[]): ShortlistItem[] {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event.type !== "tool.result" || event.payload?.tool !== "quotation_compare_tool") continue;
    return (event.payload?.shortlist as ShortlistItem[] | undefined) ?? [];
  }
  return [];
}

function money(value: number | null, currency: string | null): string {
  return value == null ? "Unknown" : `${value.toFixed(3)} ${currency ?? ""}`.trim();
}

export default function QuoteComparison({ events }: { events: TradeEvent[] }) {
  const shortlist = latestShortlist(events);
  if (!shortlist.length) return null;

  return (
    <section className="quote-panel">
      <div className="section-head">
        <div>
          <h2>Top-3 Quote Comparison</h2>
          <p>Effective Cost 为可复算的 Estimated / Partial Cost，不代表 landed cost。</p>
        </div>
      </div>
      <div className="quote-table-wrap">
        <table className="quote-table">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Unit Price</th>
              <th>Effective Cost</th>
              <th>MOQ</th>
              <th>Lead</th>
              <th>Score</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {shortlist.map((item) => (
              <tr key={item.supplier_id}>
                <td><b>#{item.rank} {item.company_name}</b><small>{item.supplier_id}</small></td>
                <td>{money(item.unit_price, item.currency)}</td>
                <td>{money(item.effective_unit_cost, item.currency)}{item.cost_is_partial ? <small>Partial</small> : null}</td>
                <td>{item.moq ?? "Unknown"}</td>
                <td>{item.lead_time_days == null ? "Unknown" : `${item.lead_time_days}d`}</td>
                <td><b>{item.final_score.toFixed(1)}</b></td>
                <td>{item.risks[0] ?? "No material risk flagged"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="approval-note">任何询价、议价、定标、合同或付款动作都需要人工确认。</div>
    </section>
  );
}
