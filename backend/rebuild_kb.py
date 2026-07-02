"""重建知识库（过滤无关景点数据）"""
import sys
sys.path.insert(0, ".")
from services.rag_service import get_knowledge_processor

# 清理并重建
rag = get_knowledge_processor()
rag.vector_db.delete_collection()

# 重新构建（现在xlsx提取已自动过滤）
count = rag.build_knowledge_base()
print(f"知识库重建完成，共 {count} 个文档块")
print(f"向量库文档数: {rag.get_document_count()}")

# 验证检索质量
test_queries = ["门票多少钱", "大佛有多高", "怎么坐车", "有什么路线", "表演时间"]
for q in test_queries:
    results = rag.search_knowledge(q, top_k=3)
    print(f"\n'{q}':")
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r['text'][:80]}...")