import React from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface MarkdownTextProps {
  text: string;
}

// whitespace-pre-wrap on every text block, not just the outer div: the MEASURED
// table from the backend aligns its columns with runs of spaces, and markdown
// would otherwise collapse them. Soft line breaks survive as "\n" text nodes,
// so pre-wrap is enough to keep the table shaped without <br> handling.
const BLOCK = 'whitespace-pre-wrap m-0 mt-3 first:mt-0';
const HEADING =
  'text-[#efb027] font-bold tracking-widest uppercase text-sm mt-4 first:mt-0 mb-1';

const components: Components = {
  p: ({ children }) => <p className={BLOCK}>{children}</p>,

  // The backend underlines "MEASURED - lithology model" with dashes, which is a
  // setext heading. Render it as the section header it was meant to be.
  h1: ({ children }) => <h2 className={HEADING}>{children}</h2>,
  h2: ({ children }) => <h2 className={HEADING}>{children}</h2>,
  h3: ({ children }) => <h3 className={HEADING}>{children}</h3>,

  strong: ({ children }) => <strong className="text-[#efb027] font-bold">{children}</strong>,
  em: ({ children }) => <em className="text-[#d8c9a3] italic">{children}</em>,

  ul: ({ children }) => <ul className="list-disc pl-5 mt-3 first:mt-0 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mt-3 first:mt-0 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="whitespace-pre-wrap">{children}</li>,

  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-[#efb027] underline underline-offset-2"
    >
      {children}
    </a>
  ),

  code: ({ children }) => (
    <code className="bg-[#2e2308] border border-[#4a3813] rounded px-1 py-0.5 text-[#efb027]">
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="bg-[#1b1305] border border-[#4a3813] rounded p-2 mt-3 overflow-x-auto">
      {children}
    </pre>
  ),

  // Tables scroll inside their own box: the chat column is narrow and a wide
  // lithology table must not push the whole panel sideways.
  table: ({ children }) => (
    <div className="mt-3 first:mt-0 overflow-x-auto">
      <table className="border-collapse text-sm w-full">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-[#2e2308]">{children}</thead>,
  th: ({ children }) => (
    <th className="border border-[#4a3813] px-2 py-1 text-left text-[#efb027] font-bold uppercase tracking-wider whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-[#4a3813] px-2 py-1 align-top">{children}</td>
  ),

  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-[#4a3813] pl-3 mt-3 text-[#c7b58c]">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="border-[#4a3813] my-3" />,
};

export const MarkdownText: React.FC<MarkdownTextProps> = ({ text }) => (
  // select-text overrides the app-root select-none: the answer is the product,
  // so it has to be selectable for copy/paste into a report.
  // KaTeX builds its layout out of nested spans, so the pre-wrap the MEASURED
  // table needs would inject stray gaps into every equation -- reset it there.
  // Display equations get their own scroll box for the same reason tables do.
  <div
    className="text-[#e8ddc7] text-base font-mono leading-relaxed select-text cursor-text
               [&_.katex]:whitespace-normal [&_.katex-display]:overflow-x-auto
               [&_.katex-display]:overflow-y-hidden [&_.katex-display]:py-1"
  >
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={components}
    >
      {text}
    </ReactMarkdown>
  </div>
);
