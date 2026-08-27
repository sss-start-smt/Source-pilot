import type { FilteredSupplier, RFQSummary, SupplierCard, TradeEvent } from "../types";

interface SupplierSearchSnapshot {
  hits: SupplierCard[];
  filtered: FilteredSupplier[];
  rfq?: RFQSummary;
}

function latestSupplierSearch(events: TradeEvent[]): SupplierSearchSnapshot {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event.type !== "tool.result" || event.payload?.tool !== "supplier_search_tool") continue;
    return {
      hits: (event.payload?.hits as SupplierCard[] | undefined) ?? [],
      filtered: (event.payload?.filtered_out as FilteredSupplier[] | undefined) ?? [],
      rfq: event.payload?.rfq as RFQSummary | undefined,
    };
  }
  return { hits: [], filtered: [] };
}

function displayValue(value: number | null | undefined, suffix = ""): string {
  return value === null || value === undefined ? "Unknown" : `${value}${suffix}`;
}

export default function SupplierCards({ events }: { events: TradeEvent[] }) {
  const { hits, filtered, rfq } = latestSupplierSearch(events);
  if (!hits.length && !rfq) return null;

  return (
    <section className="sourcing-panel">
      <div className="section-head">
        <div>
          <h2>Qualified Suppliers</h2>
          <p>只有通过当前硬约束的供应商会进入候选区。</p>
        </div>
        {rfq && (
          <div className="rfq-chip">
            {rfq.product} · {rfq.quantity} pcs
            {rfq.target_price != null ? ` · ≤ ${rfq.target_price} ${rfq.currency}` : ""}
          </div>
        )}
      </div>

      <div className="supplier-cards">
        {hits.map((supplier) => (
          <article key={supplier.supplier_id} className="supplier-card">
            <header>
              <div>
                <strong>{supplier.company_name}</strong>
                <span>{supplier.business_type} · {supplier.source}</span>
              </div>
              <div className="match-score">Match {supplier.score <= 1 ? `${(supplier.score * 100).toFixed(1)}%` : supplier.score.toFixed(2)}</div>
            </header>
            <div className="supplier-grid">
              <div><label>Unit Price</label><b>{displayValue(supplier.unit_price)} {supplier.currency}</b></div>
              <div><label>MOQ</label><b>{displayValue(supplier.moq, " pcs")}</b></div>
              <div><label>Lead Time</label><b>{displayValue(supplier.lead_time_days, " days")}</b></div>
              <div><label>Reliability</label><b>{supplier.reliability_score == null ? "Unknown" : `${(supplier.reliability_score * 100).toFixed(0)}%`}</b></div>
            </div>
            <div className="tag-row">
              {(supplier.certifications ?? []).map((item) => <span key={item}>{item}</span>)}
              {(supplier.customization ?? []).map((item) => <span key={item}>{item}</span>)}
            </div>
            <div className="hard-pass">Hard constraints passed</div>
          </article>
        ))}
      </div>

      {filtered.length > 0 && (
        <details className="filtered-out">
          <summary>查看被硬约束过滤的供应商（当前展示 {filtered.length}）</summary>
          <ul>
            {filtered.slice(0, 8).map((item) => (
              <li key={item.supplier_id}>
                <b>{item.company_name ?? item.supplier_id}</b>：{item.reason_codes.join(", ")}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
