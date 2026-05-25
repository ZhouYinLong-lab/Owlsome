# BGE Retrieval Adapter 测试记录

## 2026-05-25 可插拔检索层初始验证

### 目标

验证新增 retrieval 适配层在模型服务未部署时不会影响现有 demo，并为未来接入 `BAAI/bge-m3` 与 `BAAI/bge-reranker-v2-m3` 预留配置入口。

### 当前设计

| 项目 | 状态 |
|---|---|
| 默认 provider | `off` |
| Embedding 模型 | `BAAI/bge-m3` |
| Reranker 模型 | `BAAI/bge-reranker-v2-m3` |
| API key | 可选，本地部署可留空 |
| 向量库 | 第一版不引入，使用临时内存索引 |
| fallback | 当前关键词规则匹配 |

### 验证场景

1. `RETRIEVAL_PROVIDER=off`
   - `retrieval_probe.py` 应显示 `retrieval_fallback: True`。
   - 最终匹配结果来自 `notes.find_best_match()` 的关键词规则。

2. `RETRIEVAL_PROVIDER=custom_http` 但未配置 `EMBEDDING_BASE_URL`
   - CLI 不应崩溃。
   - 应显示缺少 `EMBEDDING_BASE_URL` 并回退规则匹配。

3. 回归验证
   - 样例导入仍可用。
   - `create_note()` 在无检索服务时仍能进入 pending。
   - `create_from_personal_point()` 继续复用 `find_best_match()`，无检索服务时仍可推荐公共知识点。

### 实测结果

provider off：

```text
provider: off
embedding_model: BAAI/bge-m3
reranker_model: BAAI/bge-reranker-v2-m3
documents: 8
retrieval_fallback: True
retrieval_reason: RETRIEVAL_PROVIDER=off，使用规则匹配 fallback。
final_match_id: 3
final_reason: 根据关键词 二重极限 自动匹配到 5.1.3 多元函数的极限。
```

配置缺失：

```text
provider: custom_http
documents: 8
retrieval_fallback: True
retrieval_reason: 未配置 EMBEDDING_BASE_URL。
final_match_id: 1
```

临时库回归：

```text
note_status pending matched 1
contribution_status pending recommended 1
pending_contributions 1
```

mock HTTP：

```text
fallback False
count 3
5 5.2.1 偏导数 1.0
6 5.2.2 高阶偏导数 1.0
7 5.2.3 全微分 1.0
```

结论：检索层默认关闭时不影响现有 demo；配置缺失时能回退；模拟 embedding/rerank 路径可以返回 Top-K 候选。

### 后续待测

上级模型服务部署完成后，需要补充：

- `openai_compatible` `/embeddings` 实测。
- `custom_http` `/embed` 实测。
- `custom_http` `/rerank` 实测。
- 和规则匹配 Top-3 命中率对比。
