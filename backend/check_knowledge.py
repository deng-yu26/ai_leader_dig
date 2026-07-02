"""快速查询知识库数据分布"""
import sys
sys.path.insert(0, '.')

from flask import Flask
from models import db, Knowledge, KnowledgeCategory, FaqKnowledge
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config["SECRET_KEY"] = SECRET_KEY
db.init_app(app)

with app.app_context():
    faq_count = FaqKnowledge.query.count()
    new_count = Knowledge.query.filter_by(is_active=True).count()
    print(f"faq_knowledge 表: {faq_count} 条")
    print(f"knowledge 表: {new_count} 条 (有效)")

    print("\n--- knowledge 表各类型 ---")
    cats = KnowledgeCategory.query.filter_by(is_active=True).all()
    for cat in cats:
        c = Knowledge.query.filter_by(category_id=cat.id, is_active=True).count()
        print(f"  {cat.name} ({cat.code}): {c} 条")

    print(f"\n--- 列表合并后总数: {faq_count + new_count} 条 ---")
    print(f"--- 每页 20 条，需要 { (faq_count + new_count + 19) // 20 } 页 ---")

    # 查看 knowledge 表中非 FAQ 的条目
    faq_cat = KnowledgeCategory.query.filter_by(code="faq").first()
    if faq_cat:
        non_faq = Knowledge.query.filter(
            Knowledge.category_id != faq_cat.id,
            Knowledge.is_active == True
        ).all()
        print(f"\n--- knowledge 表中非 FAQ 条目 ({len(non_faq)} 条) ---")
        for k in non_faq:
            cat_name = k.category.name if k.category else "无"
            print(f"  [{k.id}] {cat_name}: {k.title[:50]}")
    else:
        print("\n[!] faq 分类不存在")