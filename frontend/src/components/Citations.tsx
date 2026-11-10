// 引用清單：編號對應回答中的 [n]，像頁邊的註腳。
import type { Citation } from "../lib/sse";

export function Citations({ items, onOpen }: { items: Citation[]; onOpen?: (id: string) => void }) {
  if (items.length === 0) return null;
  return (
    <div className="turn-cites">
      {items.map((c, i) =>
        onOpen ? (
          <button key={c.id} type="button" className="cite" style={{ border: 0, cursor: "pointer" }}
                  onClick={() => onOpen(c.id)} title={c.title}>
            <span className="cite-n">{i + 1}</span>
            <span className="truncate" style={{ maxWidth: 280 }}>{c.title}</span>
          </button>
        ) : (
          <a key={c.id} className="cite" href={c.link || undefined} target="_blank"
             rel="noopener noreferrer" title={c.title}>
            <span className="cite-n">{i + 1}</span>
            <span className="truncate" style={{ maxWidth: 280 }}>{c.title}</span>
          </a>
        ),
      )}
    </div>
  );
}
