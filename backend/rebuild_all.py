"""重建纯净知识库：过滤无关景点数据 + 同步热门问答"""
import sys
sys.path.insert(0, ".")
from services.rag_service import get_knowledge_processor
from models import db, FaqKnowledge
from app import create_app

rag = get_knowledge_processor()
rag.vector_db.delete_collection()

# 重建知识库（xlsx已自动过滤为灵山相关数据）
count = rag.build_knowledge_base()
print(f"知识库重建完成，共 {count} 个文档块")

# 同步热门问答到向量库
app = create_app()
with app.app_context():
    faqs = FaqKnowledge.query.filter_by(doc_source="热门问答").all()
    faq_docs = []
    for faq in faqs:
        faq_docs.append({
            "id": f"faq_{faq.id}",
            "text": f"问题：{faq.question}\n答案：{faq.answer}",
            "metadata": {"source": faq.doc_source, "type": "faq"}
        })
    if faq_docs:
        rag.vector_db.add_documents(faq_docs)
        print(f"热门问答同步完成，共 {len(faq_docs)} 条")

    FaqKnowledge.query.update({FaqKnowledge.vector_sync: True})
    db.session.commit()

total = rag.get_document_count()
print(f"\n知识库总量：{total} 个文档块")