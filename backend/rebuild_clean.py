"""重建向量库（仅保留灵山相关数据）"""
import sys
sys.path.insert(0, ".")
from services.rag_service import get_knowledge_processor
from models import db, FaqKnowledge
from app import create_app

# 删除旧向量库
rag = get_knowledge_processor()
rag.vector_db.delete_collection()

# 重建知识库（仅灵山数据）
count = rag.build_knowledge_base()
print(f"知识库重建完成，共 {count} 个文档块")

# 添加热门问答到向量库
print("正在同步热门问答...")
app = create_app()
with app.app_context():
    unsynced = FaqKnowledge.query.filter_by(vector_sync=False).all()
    faq_docs = []
    for faq in unsynced:
        faq_docs.append({
            "id": f"faq_{faq.id}",
            "text": f"问题：{faq.question}\n答案：{faq.answer}",
            "metadata": {"source": faq.doc_source, "type": "faq"}
        })

    if faq_docs:
        rag.vector_db.add_documents(faq_docs)
        print(f"热门问答同步完成，共 {len(faq_docs)} 条")

    FaqKnowledge.query.filter_by(vector_sync=False).update({FaqKnowledge.vector_sync: True})
    db.session.commit()

total = rag.get_document_count()
print(f"\n知识库总量：{total} 个文档块")
print(f"其中文档 {count} 块 + FAQ {len(faq_docs)} 条")

# 测试检索
print("\n===== 检索测试 =====")
test_queries = ["门票多少钱", "大佛有多高", "怎么坐车", "有什么路线", "表演几点有"]
for q in test_queries:
    results = rag.search_knowledge(q, top_k=3)
    print(f"\n'{q}':")
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r['text'][:80]}...")