// Markdown 渲染。react-markdown 預設不解析原始 HTML、會過濾 javascript: 連結；
// 這裡再讓所有連結另開分頁且不帶 referrer / opener。
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children, small }: { children: string; small?: boolean }) {
  return (
    <div className={small ? "prose prose-sm" : "prose"}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children: label }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">{label}</a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
