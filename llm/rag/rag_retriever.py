from langchain_core.tools import tool
from llm.rag.exercise_vectorstore import get_store, _load_exercise_json

@tool
def search_exercise_knowledge(query: str) -> str:
    """
    通过语义搜索在健身动作知识库中检索相关动作信息。
    适用场景：用户询问某个肌肉部位有哪些动作、动作标准做法、器械选择、可替代动作等。
    Args:
        query: 自然语言查询，例如 "练胸的哑铃动作" 或 "背阔肌孤立训练"
    """
    all_docs = []

    # 1. 拿到向量库（首次调用会自动建库）
    core_store = get_store("exercises", doc_loader_fn=_load_exercise_json)
    core_docs = core_store.as_retriever(
        search_type = "mmr",
        search_kwargs = {"k" : 3, "fetch_k": 10},
    ).invoke(query)

    all_docs.extend(core_docs)  # extend 而不是 append，core_docs 是列表

    if not all_docs:
        return f"未找到与「{query}」相关的健身知识。"

    parts = []
    for i, doc in enumerate(all_docs, 1):
        m = doc.metadata
        if m.get("name"):
            source_tag = f"动作库：{m.get('name')}"
            detail = (
                f"  主要部位：{m.get('primary_muscles')}  "
                f"辅助：{m.get('secondary_muscles')}\n"
                f"  器械：{m.get('equipment')}  "
                f"难度：{m.get('level')}\n"
                f"  动作ID：{m.get('id')}\n"
                f"  做法摘要：{doc.page_content[doc.page_content.find('动作说明：')+5:][:150]}"
            )
        else:
            source_tag = f"指导手册：{m.get('source', '未知来源')}"
            detail = doc.page_content[:300]

        parts.append(f"【{i}】{source_tag}\n{detail}")

    return f"共找到 {len(all_docs)} 条相关内容：\n\n" + "\n\n".join(parts)