import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeKatex from "rehype-katex";

type ObsidianBlock =
  | { type: "markdown"; content: string }
  | { type: "callout"; kind: string; title: string; content: string; folded: boolean };

const katexOptions = {
  throwOnError: false,
  strict: false
};

const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "mark"]
};

const calloutLabels: Record<string, string> = {
  abstract: "摘要",
  bug: "问题",
  danger: "危险",
  error: "错误",
  example: "示例",
  failure: "失败",
  faq: "问答",
  help: "帮助",
  hint: "提示",
  important: "重点",
  info: "信息",
  note: "笔记",
  question: "问题",
  quote: "引用",
  success: "成功",
  summary: "摘要",
  tip: "提示",
  todo: "待办",
  warning: "警告"
};

function preprocessObsidianInlineSyntax(markdown: string) {
  return markdown
    .replace(/^---\n[\s\S]*?\n---\n?/, "")
    .replace(/!\[\[([^\]]+)\]\]/g, (_match, target) => `![${target}](${target})`)
    .replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (_match, target, label) => `[${label}](#wikilink-${encodeURIComponent(target)})`)
    .replace(/\[\[([^\]]+)\]\]/g, (_match, target) => `[${target}](#wikilink-${encodeURIComponent(target)})`)
    .replace(/==(.+?)==/g, "<mark>$1</mark>");
}

function stripFrontmatter(markdown: string) {
  return markdown.replace(/^---\n[\s\S]*?\n---\n?/, "");
}

function parseObsidianBlocks(markdown: string): ObsidianBlock[] {
  const lines = stripFrontmatter(markdown).split(/\r?\n/);
  const blocks: ObsidianBlock[] = [];
  let buffer: string[] = [];

  function flushMarkdown() {
    const content = buffer.join("\n").trim();
    if (content) blocks.push({ type: "markdown", content });
    buffer = [];
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const match = line.match(/^>\s*\[!([a-zA-Z-]+)\]([+-])?\s*(.*)$/);

    if (!match) {
      buffer.push(line);
      continue;
    }

    flushMarkdown();
    const kind = match[1].toLowerCase();
    const folded = match[2] === "-";
    const title = (match[3] || calloutLabels[kind] || kind).trim();
    const body: string[] = [];

    // Obsidian callouts are contiguous blockquote lines beginning with > [!type].
    while (index + 1 < lines.length && /^>\s?/.test(lines[index + 1])) {
      index += 1;
      body.push(lines[index].replace(/^>\s?/, ""));
    }

    blocks.push({ type: "callout", kind, title, content: body.join("\n").trim(), folded });
  }

  flushMarkdown();
  return blocks;
}

function MarkdownSource({ children, inline = false }: { children: string; inline?: boolean }) {
  const rendered = preprocessObsidianInlineSyntax(children);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema], [rehypeKatex, katexOptions]]}
      components={inline ? { p: React.Fragment } : undefined}
    >
      {rendered}
    </ReactMarkdown>
  );
}

export function Markdown({ children }: { children: string }) {
  const blocks = parseObsidianBlocks(children);
  return (
    <div className="markdown-body">
      {blocks.map((block, index) => {
        if (block.type === "callout") {
          return (
            <div className={`obsidian-callout obsidian-callout-${block.kind}`} key={`${block.kind}-${index}`}>
              <div className="obsidian-callout-title">
                <span>{calloutLabels[block.kind] ?? block.kind}</span>
                <strong>{block.title}</strong>
              </div>
              {block.content && <MarkdownSource>{block.content}</MarkdownSource>}
            </div>
          );
        }
        return <MarkdownSource key={`markdown-${index}`}>{block.content}</MarkdownSource>;
      })}
    </div>
  );
}

export function InlineMarkdown({ children }: { children: string }) {
  return (
    <span className="markdown-inline">
      <MarkdownSource inline>{children}</MarkdownSource>
    </span>
  );
}
