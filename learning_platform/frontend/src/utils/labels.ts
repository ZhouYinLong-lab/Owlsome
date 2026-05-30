import type { Role, Tab } from "../types";

export function unitLabel(type: string) {
  const labels: Record<string, string> = {
    explanation: "讲解",
    definition: "定义",
    theorem: "定理",
    example: "例题",
    exercise: "习题"
  };
  return labels[type] ?? type;
}

export function sourceLabel(source?: string) {
  if (!source) return "";
  if (source.startsWith("community_contribution:")) return "社区贡献";
  if (source.includes("text_archiver")) return "清洗版教材";
  if (source.includes("MinerU")) return "MinerU 原文";
  return source;
}

export function progressLabel(status: string) {
  const labels: Record<string, string> = {
    not_started: "未开始",
    learning: "学习中",
    mastered: "已掌握",
    difficult: "疑难点"
  };
  return labels[status] ?? status;
}

export function contributionLabel(type: string) {
  const labels: Record<string, string> = {
    note: "笔记",
    explanation: "讲解",
    example: "例题",
    exercise: "习题",
    mistake: "易错点",
    faq: "FAQ"
  };
  return labels[type] ?? type;
}

export function pageMeta(tab: Tab, role: Role) {
  const adminSuffix = role === "admin" ? " · 管理员模式" : "";
  const meta: Record<Tab, { eyebrow: string; title: string }> = {
    dashboard: {
      eyebrow: `Owlsome Learning${adminSuffix}`,
      title: "今天从哪里开始学习？"
    },
    knowledge: {
      eyebrow: "公共资源库",
      title: "按学科、教材和章节浏览公共知识"
    },
    personal: {
      eyebrow: "个人学习空间",
      title: "把自己的资料整理成可问答的学习路径"
    },
    pipeline: {
      eyebrow: "资料处理链路",
      title: "从 PDF 到 Obsidian Markdown，再到知识库"
    },
    review: {
      eyebrow: "管理员工作台",
      title: "审核贡献与笔记，决定哪些内容进入公共库"
    },
    system: {
      eyebrow: "系统概览",
      title: "查看演示数据、导入状态和运行指标"
    },
    exercises: {
      eyebrow: "管理员工作台",
      title: "管理题目并绑定到知识点"
    }
  };
  return meta[tab];
}
