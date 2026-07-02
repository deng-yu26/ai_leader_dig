"""
==============================================================
知识库迁移脚本
功能：
  1. 将旧 faq_knowledge 表的数据永久迁移到新 knowledge 表
  2. 扫描 knowledge/ 目录中的文档，按类型自动识别并导入新表
  3. 同步更新向量库（ChromaDB）
==============================================================
"""

import os
import sys
import re
import json
from collections import Counter
from datetime import datetime

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, FaqKnowledge, Knowledge, KnowledgeCategory
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
)


def create_app():
    """创建一个临时的Flask应用用于数据库操作"""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    db.init_app(app)
    return app


def extract_keywords(text, top_k=8):
    """简单的关键词提取（高频词）"""
    words = re.findall(r'[\u4e00-\u9fff]+', text)
    words = [w for w in words if len(w) >= 2]
    counter = Counter(words)
    stopwords = {
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
        "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些", "什么", "怎么",
        "哪", "谁", "为什么", "因为", "所以", "但是", "如果", "可以", "这样", "那样",
        "这个", "那个", "这些", "那些", "来", "过", "做", "用", "比", "对", "给",
        "从", "被", "把", "让", "得", "地", "还", "只", "又", "再", "很",
        "非常", "已经", "可能", "应该", "不会", "不能", "还是", "或者", "以及",
        "问题", "答案", "文档", "手动", "录入", "知识", "管理", "系统",
    }
    filtered = {w: c for w, c in counter.items() if w not in stopwords}
    return [w for w, _ in Counter(filtered).most_common(top_k)]


def detect_category(text):
    """根据文本内容自动检测知识类型"""
    scene_keywords = ["景点", "讲解", "介绍", "景观", "建筑", "佛像", "大佛", "梵宫"]
    history_keywords = ["历史", "文化", "古代", "朝代", "佛教", "传统", "习俗", "典故"]
    info_keywords = ["门票", "交通", "停车", "开放时间", "价格", "门票价格", "游玩时间", "交通", "停车"]
    route_keywords = ["路线", "行程", "攻略", "游览", "推荐路线", "游玩顺序"]
    faq_patterns = ["如何", "怎么", "什么", "吗", "?", "？"]

    text_lower = text.lower()
    scores = {
        "faq": sum(1 for q in faq_patterns if q in text_lower),
        "scene_intro": sum(1 for kw in scene_keywords if kw in text_lower),
        "history": sum(1 for kw in history_keywords if kw in text_lower),
        "basic_info": sum(1 for kw in info_keywords if kw in text_lower),
        "route": sum(1 for kw in route_keywords if kw in text_lower),
    }

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "faq"


def read_docx_text(file_path):
    """读取 docx 文件"""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except ImportError:
        return None
    except Exception as e:
        print(f"  [x] docx解析失败: {e}")
        return None


def read_xlsx_text(file_path):
    """读取 xlsx 文件"""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(file_path, data_only=True)
        texts = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                texts.append("\t".join([str(c) for c in row if c is not None]))
        return "\n".join(texts)
    except ImportError:
        return None
    except Exception as e:
        print(f"  [x] xlsx解析失败: {e}")
        return None


def read_txt_text(file_path):
    """读取 txt 文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="gbk") as f:
                return f.read()
        except Exception as e:
            print(f"  [x] txt解析失败: {e}")
            return None
    except Exception as e:
        print(f"  [x] txt解析失败: {e}")
        return None


def read_pdf_text(file_path):
    """读取 pdf 文件"""
    try:
        import fitz
        doc = fitz.open(file_path)
        return "\n".join([page.get_text() for page in doc])
    except ImportError:
        print(f"  [!] PDF库PyMuPDF未安装，跳过PDF文件")
        return None
    except Exception as e:
        print(f"  [x] pdf解析失败: {e}")
        return None


def get_file_text(file_path):
    """根据文件扩展名自动选择读取方式"""
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".docx":
        return read_docx_text(file_path)
    elif ext == ".xlsx":
        return read_xlsx_text(file_path)
    elif ext == ".txt":
        return read_txt_text(file_path)
    elif ext == ".pdf":
        return read_pdf_text(file_path)
    return None


# ======================== 1. 迁移 FAQ 数据 ========================
def migrate_faq(app):
    """将旧 faq_knowledge 表数据迁移到知识表"""
    with app.app_context():
        faq_cat = KnowledgeCategory.query.filter_by(code="faq").first()
        if not faq_cat:
            print("[!] faq分类不存在，无法迁移")
            return 0

        faqs = FaqKnowledge.query.all()
        migrated = 0
        skipped = 0

        print(f"\n[迁移] 共发现 {len(faqs)} 条 FAQ 记录")

        for faq in faqs:
            # 跳过文件上传类（标题以【文件】开头），这些会在步骤2处理
            if faq.question and faq.question.startswith("【文件】"):
                skipped += 1
                continue

            # 检测是否为纯FAQ还是其他类型
            combined = (faq.question or "") + "\n" + (faq.answer or "")
            detected = detect_category(combined)
            cat = KnowledgeCategory.query.filter_by(code=detected).first()
            if not cat:
                cat = faq_cat  # 默认FAQ

            keywords = extract_keywords(combined, top_k=6)

            knowledge = Knowledge(
                category_id=cat.id,
                title=faq.question,
                content=faq.answer,
                tags=", ".join(keywords),
                source_file=faq.doc_source or "faq迁移",
                keywords=", ".join(keywords),
                version=1,
                vector_sync=faq.vector_sync,
                is_active=True,
                sort_order=0,
            )
            db.session.add(knowledge)
            migrated += 1

        db.session.commit()
        print(f"[迁移] 成功: {migrated} 条")
        print(f"[迁移] 跳过（文件类）: {skipped} 条")
        return migrated


# ======================== 2. 扫描 knowledge/ 目录并导入 ========================
def scan_knowledge_docs(app):
    """扫描知识文档目录，自动识别类型并导入"""
    with app.app_context():
        knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")
        if not os.path.isdir(knowledge_dir):
            print(f"\n[扫描] 知识目录不存在: {knowledge_dir}")
            return 0

        files = [
            f for f in os.listdir(knowledge_dir)
            if os.path.isfile(os.path.join(knowledge_dir, f))
            and f.lower().endswith((".docx", ".xlsx", ".txt", ".pdf"))
        ]
        print(f"\n[扫描] 知识目录: {knowledge_dir}")
        print(f"[扫描] 共发现 {len(files)} 个文档文件")

        imported = 0
        skipped = 0

        for filename in files:
            filepath = os.path.join(knowledge_dir, filename)
            print(f"\n  >> 处理: {filename}")

            text = get_file_text(filepath)
            if not text or len(text.strip()) < 10:
                print(f"      [x] 内容为空或过短，跳过")
                skipped += 1
                continue

            # 检测类型
            detected = detect_category(text)
            print(f"      [√] 检测到类型: {detected}")

            cat = KnowledgeCategory.query.filter_by(code=detected).first()
            if not cat:
                cat = KnowledgeCategory.query.filter_by(code="faq").first()
                if not cat:
                    print(f"      [x] 无可用分类，跳过")
                    skipped += 1
                    continue

            # 检查是否已存在（按文件名去重）
            existing = Knowledge.query.filter_by(source_file=filename).first()
            if existing:
                print(f"      [!] 已存在，跳过")
                skipped += 1
                continue

            keywords = extract_keywords(text, top_k=8)
            print(f"      [√] 提取关键词: {', '.join(keywords)}")

            # 截断内容用于展示
            title = os.path.splitext(filename)[0]
            content = text[:3000] + ("..." if len(text) > 3000 else "")

            knowledge = Knowledge(
                category_id=cat.id,
                title=f"【文档】{title}",
                content=content,
                tags=", ".join(keywords),
                source_file=filename,
                keywords=", ".join(keywords),
                version=1,
                vector_sync=True,
                is_active=True,
                sort_order=0,
            )
            db.session.add(knowledge)
            imported += 1

        db.session.commit()
        print(f"\n[扫描] 成功导入: {imported} 条")
        print(f"[扫描] 跳过（已存在/无效）: {skipped} 条")
        return imported


# ======================== 3. 同步向量库 ========================
def sync_vector_db(app):
    """将新导入的知识同步到 ChromaDB 向量库"""
    with app.app_context():
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from services.rag_service import get_knowledge_processor
            processor = get_knowledge_processor()

            unsynced = Knowledge.query.filter_by(vector_sync=False).all()
            if not unsynced:
                print("\n[向量] 无需同步，所有条目已同步")
                return 0

            print(f"\n[向量] 待同步 {len(unsynced)} 条知识到 ChromaDB...")

            for k in unsynced:
                processor.vector_db.add_documents([{
                    "id": f"knowledge_{k.id}",
                    "text": f"标题：{k.title}\n内容：{k.content}",
                    "metadata": {
                        "source": k.category.name if k.category else "未知",
                        "type": k.category.code if k.category else "unknown",
                        "id": k.id,
                    }
                }])
                k.vector_sync = True

            db.session.commit()
            print(f"[向量] 同步完成，共 {len(unsynced)} 条")
            return len(unsynced)
        except Exception as e:
            print(f"[向量] 同步失败: {e}")
            return 0


# ======================== 4. 统计报告 ========================
def print_report(app):
    """打印迁移后的统计报告"""
    with app.app_context():
        print("\n" + "=" * 50)
        print("知识库迁移完成 — 统计报告")
        print("=" * 50)

        categories = KnowledgeCategory.query.filter_by(is_active=True).all()
        for cat in categories:
            count = Knowledge.query.filter_by(category_id=cat.id, is_active=True).count()
            print(f"  {cat.name:　<8} ({cat.code:　<12}): {count} 条")

        print("-" * 50)
        total = Knowledge.query.filter_by(is_active=True).count()
        faq_total = FaqKnowledge.query.count()
        print(f"  knowledge 表:   {total} 条（通用知识库）")
        print(f"  faq_knowledge:  {faq_total} 条（旧FAQ表，保留兼容）")
        print("=" * 50)


# ======================== 主入口 ========================
def main():
    app = create_app()

    with app.app_context():
        # 确保分类初始化
        KnowledgeCategory.init_defaults()

        print("=" * 50)
        print("知识库迁移脚本")
        print("=" * 50)

        # 步骤1：迁移FAQ数据
        migrate_faq(app)

        # 步骤2：扫描文档并导入
        scan_knowledge_docs(app)

        # 步骤3：同步向量库
        sync_vector_db(app)

        # 步骤4：统计报告
        print_report(app)

        print("\n[✓] 迁移脚本执行完成！")


if __name__ == "__main__":
    main()