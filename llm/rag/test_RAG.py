# 运行方式：在项目根目录执行
# python -m llm.rag.test_rag
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from llm.rag.rag_retriever import search_exercise_knowledge

test_queries = [
    "练胸肌的动作",
    "三角肌是什么肌肉",
    "深蹲替代动作",
]

for query in test_queries:
    print(f"\n{'='*50}")
    print(f"查询：{query}")
    print('='*50)

    result = search_exercise_knowledge.invoke({"query": query})
    print(result)