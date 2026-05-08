import json
from pathlib import Path

from langchain_community.utils.math import cosine_similarity
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from markdown2 import markdown
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from models.MemorySummary_Model import MemorySummary

_ROOT = Path(__file__).parent.parent.parent   # 往上三级到项目根目录
_EXERCISE_JSON = _ROOT / "db" / "exercise.json"
_CHAMPION_BOOK_MD = _ROOT / "data" / "document" / "世界冠军健身全书-177-209.md"
_CHROMA_DIR = str(_ROOT / "data" / "chroma_db")
_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_cache : dict[str, Chroma] = {}
_embeddings = None

def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=_EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings

# 读取exercise.json并转化成langchain.document格式
def _load_exercise_json():
    with open(_EXERCISE_JSON, "r", encoding="utf-8") as f:
        exercises = json.load(f)

    docs = []
    for ex in exercises:
        # 拼成自然语言——Embedding 模型理解语义靠这段文字
        text = (
            f"动作名称：{ex['name']}\n"
            f"主要训练部位：{'、'.join(ex.get('primaryMuscles', []))}\n"
            f"辅助肌肉：{'、'.join(ex.get('secondaryMuscles', []))}\n"
            f"所需器械：{ex.get('equipment', '未知')}\n"
            f"难度等级：{ex.get('level', '未知')}\n"
            f"动作类型：{ex.get('mechanic', '未知')}\n"
            f"动作说明：{''.join(ex.get('instructions', []))}"
        )
        doc = Document(
            page_content=text,
            metadata={
                "id": ex["id"],
                "name": ex["name"],
                "primary_muscles": "、".join(ex.get("primaryMuscles", [])),
                "secondary_muscles": "、".join(ex.get("secondaryMuscles", [])),
                "equipment": ex.get("equipment", ""),
                "level": ex.get("level", ""),
                "mechanic": ex.get("mechanic", ""),
            }
        )
        docs.append(doc)
    return docs


def get_store(collection_name:str,  doc_loader_fn=None):
    """
      获取指定 collection 的向量库。

      Args:
          collection_name: 集合名，如 "exercises"、"nutrition_pdf"
          doc_loader_fn:   首次建库时调用，返回 List[Document]
                           如果 collection 已有数据，此参数可不传
      """
    # 1.已加载，直接返回
    if collection_name in _cache:
        return _cache[collection_name]

    # 2. 加载（ChromaDB 自动创建不存在的 collection）
    store = Chroma(
        collection_name=collection_name,
        embedding_function=_get_embeddings(),
        persist_directory=_CHROMA_DIR,
    )
    try:
        count = store._collection.count()
    except Exception:
        count = 0

    if count == 0:
        if doc_loader_fn is None:
            print(f"ℹ️ [RAG] '{collection_name}' 目前为空，待手动存入")
        else:
            docs = doc_loader_fn()
            if docs:
                store.add_documents(docs)
                print(f"✅ [RAG] 初始化成功，存入 {len(docs)} 条")
            else:
                # loader 存在但返回空，这通常是 bug，应该警告得更明显
                print(f"⚠️ [RAG] '{collection_name}' 的 loader 返回了空列表，请检查数据源")

    else:
        print(f"📚 [RAG] '{collection_name}' 已就绪（现存 {count} 条）")

    _cache[collection_name] = store
    return store

def _load_markdown():
    with open(_CHAMPION_BOOK_MD, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    #第一层切分，根据markdown格式
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#","Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
            ("####", "Header_4"),
        ],
        strip_headers=False
    )
    header_docs = markdown_splitter.split_text(markdown_text)

    #第二层切分，分成更小的块
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=120,
        separators=["\n\n","\n","。",",","!","?"," "]
    )
    docs = recursive_splitter.split_documents(header_docs)
    return docs

# 默认直接创建summary库
memory_summaries_store = Chroma(
    collection_name="memory_summaries",
    embedding_function=_get_embeddings(),
    persist_directory=_CHROMA_DIR,
)
class ChromaService:
    @staticmethod
    async def save_summaries_to_chroma(record: MemorySummary):
        store = get_store("memory_summaries")
        await store.aadd_texts(
            texts=[record.summary_text],
            metadatas=[{
                "summary_id": record.id,
                "session_id": record.session_id,
                "thread_id": record.thread_id,
                "scope": record.scope,
                "created_at": record.created_at.isoformat() if record.created_at else None
            }],
            ids=[f"memory_summary_{record.id}"],
        )