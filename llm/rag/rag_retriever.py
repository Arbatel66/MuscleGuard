from langchain_classic.retrievers import MultiQueryRetriever
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from llm.rag.exercise_vectorstore import get_store, _load_exercise_json, _load_markdown


@tool
def search_exercise_knowledge(query: str, config: RunnableConfig) -> str:
    """
    通过语义搜索在健身动作知识库中检索相关动作信息。
    适用场景：用户询问某个肌肉部位有哪些动作、动作标准做法、器械选择、可替代动作等。
    警告：当用户询问肌肉相关知识时先调用此方法查询，如果查询不出相应结果需要告知用户后再自行回答。
    Args:
        query: 自然语言查询，例如 "练胸的哑铃动作" 或 "背阔肌孤立训练"
    todo：Rerank检索
    """
    llm = config["configurable"].get("llm")
    if llm is None:
        return "错误：未获取到LLM。"

    all_docs = []

    # 拿到向量库（首次调用会自动建库）
    core_store = get_store("exercises", doc_loader_fn=_load_exercise_json)
    champion_store = get_store("champion_book", doc_loader_fn=_load_markdown)

    # 1. collection_1开始检索
    core_docs = core_store.as_retriever(
        search_type = "mmr",
        search_kwargs = {"k" : 10, "fetch_k": 30},
    ).invoke(query)
    all_docs.extend(core_docs)  # extend 而不是 append，core_docs 是列表,extend是拆散放入

    # 2. collection_2开始检索
    champion_base_retriever = champion_store.as_retriever(
        search_type = "mmr",
        search_kwargs={"k": 5, "fetch_k": 20},
    )

    print("RAG开始执行MultiQuery")
    champion_docs = MultiQueryRetriever.from_llm(
        retriever=champion_base_retriever,
        llm=llm
    ).invoke(query)
    print("MultiQuery执行成功，添加到候选答案")
    all_docs.extend(champion_docs)

    if not all_docs:
        return f"未找到与「{query}」相关的健身知识。"
    # all_docs为候选答案列表，存了两种不同的知识库格式的数据，现在要统一格式
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
        elif m.get("Header_1"):
            source_tag = "世界冠军健身全书"
            detail = doc.page_content[:300]
        else:
            source_tag = "指导手册"
            detail = doc.page_content[:300]

        parts.append(f"【{i}】{source_tag}\n{detail}")
    print(parts)
    return f"共找到 {len(all_docs)} 条相关内容：\n\n" + "\n\n".join(parts)