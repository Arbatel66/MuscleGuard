# 运行方式：在项目根目录执行
# python -m llm.rag.test_rag

from llm.rag.rag_retriever import search_exercise_knowledge

test_queries = [
    "练胸肌的哑铃动作",
    "背阔肌孤立训练",
    "深蹲替代动作",
]

for query in test_queries:
    print(f"\n{'='*50}")
    print(f"查询：{query}")
    print('='*50)
    result = search_exercise_knowledge.invoke({"query": query})
    print(result)