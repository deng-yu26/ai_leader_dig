"""将FAQ热门问答重新同步到向量库"""
import sys
sys.path.insert(0, ".")
from models import db, FaqKnowledge
from app import create_app
from services.rag_service import get_knowledge_processor

app = create_app()
with app.app_context():
    faqs = FaqKnowledge.query.filter_by(doc_source="热门问答").all()
    print(f"找到 {len(faqs)} 条热门问答")

    processor = get_knowledge_processor()
    faq_docs = []
    for faq in faqs:
        faq_docs.append({
            "id": f"faq_{faq.id}",
            "text": f"问题：{faq.question}\n答案：{faq.answer}",
            "metadata": {"source": faq.doc_source, "type": "faq"}
        })

    if faq_docs:
        processor.vector_db.add_documents(faq_docs)
        print(f"✅ FAQ同步到向量库完成，共 {len(faq_docs)} 条")

    total = processor.get_document_count()
    print(f"知识库总量：{total} 个文档块")

    # 测试热门问答检索
    print("\n===== 热门问答检索测试 =====")
    test_queries = ["门票多少钱", "大佛有多高", "怎么坐车", "有什么路线", "表演几点有"]
    for q in test_queries:
        results = processor.search_knowledge(q, top_k=2)
        print(f"\n'{q}':")
        for i, r in enumerate(results):
            text_preview = r['text'][:60]
            print(f"  [{i+1}] {text_preview}...")
            if r['metadata'].get('type') == 'faq':
                print(f"       ^ 热门问答匹配")