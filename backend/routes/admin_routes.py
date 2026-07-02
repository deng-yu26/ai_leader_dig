"""
==============================================================
管理员路由模块
提供管理员相关的RESTful API接口
==============================================================
"""

import os
import sys
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify, session
from models import db, Admin, User, ChatLog, FaqKnowledge, DigitalHuman
from services.rag_service import get_knowledge_processor
from services.llm_service import get_llm_service

# 创建管理员蓝图
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ======================== 管理员登录鉴权装饰器 ========================
def admin_required(f):
    """要求管理员登录的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_id = session.get("admin_id")
        if not admin_id:
            return jsonify({"code": 401, "message": "请先登录"}), 401
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"code": 401, "message": "管理员不存在"}), 401
        return f(*args, **kwargs)
    return decorated


# ======================== 1. 管理员登录/登出 ========================
@admin_bp.route("/login", methods=["POST"])
def admin_login():
    """管理员登录"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数不能为空"})

    username = data.get("username", "")
    password = data.get("password", "")

    admin = Admin.query.filter_by(username=username).first()
    if not admin or not admin.check_password(password):
        return jsonify({"code": 401, "message": "账号或密码错误"})

    # 保存登录态
    session["admin_id"] = admin.id
    session["admin_username"] = admin.username

    return jsonify({
        "code": 200,
        "message": "登录成功",
        "data": admin.to_dict()
    })


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def admin_logout():
    """管理员登出"""
    session.pop("admin_id", None)
    session.pop("admin_username", None)
    return jsonify({"code": 200, "message": "已退出登录"})


@admin_bp.route("/info", methods=["GET"])
@admin_required
def admin_info():
    """获取当前管理员信息"""
    admin = Admin.query.get(session["admin_id"])
    return jsonify({"code": 200, "data": admin.to_dict()})


# ======================== 2. 管理员账号管理 ========================
@admin_bp.route("/admins", methods=["GET"])
@admin_required
def list_admins():
    """获取管理员列表"""
    admins = Admin.query.all()
    return jsonify({
        "code": 200,
        "data": [a.to_dict() for a in admins]
    })


@admin_bp.route("/admins", methods=["POST"])
@admin_required
def create_admin():
    """创建新管理员"""
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"code": 400, "message": "用户名和密码不能为空"})

    if Admin.query.filter_by(username=data["username"]).first():
        return jsonify({"code": 400, "message": "用户名已存在"})

    admin = Admin(username=data["username"])
    admin.set_password(data["password"])
    db.session.add(admin)
    db.session.commit()

    return jsonify({"code": 200, "message": "创建成功", "data": admin.to_dict()})


# ======================== 3. 游客用户管理 ========================
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """获取游客用户列表（支持分页）"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    keyword = request.args.get("keyword", "")

    query = User.query
    if keyword:
        query = query.filter(
            User.username.contains(keyword) |
            User.phone.contains(keyword) |
            User.email.contains(keyword)
        )

    pagination = query.order_by(User.registered_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "code": 200,
        "data": {
            "items": [u.to_dict() for u in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages
        }
    })


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """删除游客用户"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"code": 404, "message": "用户不存在"})

    db.session.delete(user)
    db.session.commit()
    return jsonify({"code": 200, "message": "删除成功"})


# ======================== 4. 数字人配置管理 ========================
@admin_bp.route("/digital-humans", methods=["GET"])
@admin_required
def list_digital_humans():
    """获取数字人列表"""
    humans = DigitalHuman.query.order_by(DigitalHuman.id).all()
    return jsonify({
        "code": 200,
        "data": [h.to_dict() for h in humans]
    })


@admin_bp.route("/digital-humans", methods=["POST"])
@admin_required
def create_digital_human():
    """创建数字人配置"""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"code": 400, "message": "数字人名称不能为空"})

    dh = DigitalHuman(
        name=data["name"],
        model_path=data.get("model_path", "/live2d_models/default/"),
        default_speed=data.get("default_speed", 1.0),
        default_pitch=data.get("default_pitch", 1.0),
        default_voice=data.get("default_voice", "zh-CN-XiaoxiaoNeural"),
        is_active=data.get("is_active", True)
    )
    db.session.add(dh)
    db.session.commit()

    return jsonify({"code": 200, "message": "创建成功", "data": dh.to_dict()})


@admin_bp.route("/digital-humans/<int:dh_id>", methods=["PUT"])
@admin_required
def update_digital_human(dh_id):
    """更新数字人配置"""
    dh = DigitalHuman.query.get(dh_id)
    if not dh:
        return jsonify({"code": 404, "message": "数字人不存在"})

    data = request.get_json()
    if data.get("name") is not None:
        dh.name = data["name"]
    if data.get("model_path") is not None:
        dh.model_path = data["model_path"]
    if data.get("default_speed") is not None:
        dh.default_speed = float(data["default_speed"])
    if data.get("default_pitch") is not None:
        dh.default_pitch = float(data["default_pitch"])
    if data.get("default_voice") is not None:
        dh.default_voice = data["default_voice"]
    if data.get("is_active") is not None:
        dh.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify({"code": 200, "message": "更新成功", "data": dh.to_dict()})


@admin_bp.route("/digital-humans/<int:dh_id>", methods=["DELETE"])
@admin_required
def delete_digital_human(dh_id):
    """删除数字人配置"""
    dh = DigitalHuman.query.get(dh_id)
    if not dh:
        return jsonify({"code": 404, "message": "数字人不存在"})

    db.session.delete(dh)
    db.session.commit()
    return jsonify({"code": 200, "message": "删除成功"})


# ======================== 5. 知识库管理 ========================
@admin_bp.route("/knowledge", methods=["GET"])
@admin_required
def list_knowledge():
    """获取知识库列表（支持分页）"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    keyword = request.args.get("keyword", "")

    query = FaqKnowledge.query
    if keyword:
        query = query.filter(FaqKnowledge.question.contains(keyword))

    pagination = query.order_by(FaqKnowledge.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "code": 200,
        "data": {
            "items": [k.to_dict() for k in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages
        }
    })


@admin_bp.route("/knowledge", methods=["POST"])
@admin_required
def create_knowledge():
    """创建知识条目"""
    data = request.get_json()
    if not data or not data.get("question") or not data.get("answer"):
        return jsonify({"code": 400, "message": "问题和答案不能为空"})

    knowledge = FaqKnowledge(
        question=data["question"],
        answer=data["answer"],
        doc_source=data.get("doc_source", "手动录入")
    )
    db.session.add(knowledge)
    db.session.commit()

    return jsonify({"code": 200, "message": "创建成功", "data": knowledge.to_dict()})


@admin_bp.route("/knowledge/<int:k_id>", methods=["PUT"])
@admin_required
def update_knowledge(k_id):
    """更新知识条目"""
    knowledge = FaqKnowledge.query.get(k_id)
    if not knowledge:
        return jsonify({"code": 404, "message": "知识条目不存在"})

    data = request.get_json()
    if data.get("question") is not None:
        knowledge.question = data["question"]
    if data.get("answer") is not None:
        knowledge.answer = data["answer"]
    if data.get("doc_source") is not None:
        knowledge.doc_source = data["doc_source"]

    knowledge.vector_sync = False  # 标记需要重新同步
    db.session.commit()

    return jsonify({"code": 200, "message": "更新成功", "data": knowledge.to_dict()})


@admin_bp.route("/knowledge/<int:k_id>", methods=["DELETE"])
@admin_required
def delete_knowledge(k_id):
    """删除知识条目"""
    knowledge = FaqKnowledge.query.get(k_id)
    if not knowledge:
        return jsonify({"code": 404, "message": "知识条目不存在"})

    db.session.delete(knowledge)
    db.session.commit()
    return jsonify({"code": 200, "message": "删除成功"})


@admin_bp.route("/knowledge/sync", methods=["POST"])
@admin_required
def sync_knowledge():
    """一键同步知识库到向量库（文档目录 + FAQ表）"""
    try:
        processor = get_knowledge_processor()

        # 1. 同步文档目录
        doc_count = processor.build_knowledge_base()

        # 2. 同步FAQ表中的知识（未同步的条目）
        unsynced = FaqKnowledge.query.filter_by(vector_sync=False).all()
        faq_docs = []
        for faq in unsynced:
            faq_docs.append({
                "id": f"faq_{faq.id}",
                "text": f"问题：{faq.question}\n答案：{faq.answer}",
                "metadata": {
                    "source": faq.doc_source or "手动录入",
                    "type": "faq"
                }
            })

        if faq_docs:
            processor.vector_db.add_documents(faq_docs)

        # 标记全部已同步
        FaqKnowledge.query.update({FaqKnowledge.vector_sync: True})
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": f"向量库同步完成，文档{doc_count}条 + FAQ{len(faq_docs)}条",
            "data": {"doc_count": doc_count, "faq_count": len(faq_docs)}
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"同步失败：{str(e)}"})


@admin_bp.route("/knowledge/upload", methods=["POST"])
@admin_required
def upload_knowledge_file():
    """上传知识文档文件，自动提取内容并入库"""
    if "file" not in request.files:
        return jsonify({"code": 400, "message": "未上传文件"})

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"code": 400, "message": "文件为空"})

    # 检查文件扩展名
    allowed_extensions = {"docx", "xlsx", "txt", "pdf"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_extensions:
        return jsonify({"code": 400, "message": f"不支持的文件类型，仅支持: {', '.join(allowed_extensions)}"})

    # 保存上传文件到knowledge目录
    knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "../knowledge")
    knowledge_dir = os.path.abspath(knowledge_dir)
    os.makedirs(knowledge_dir, exist_ok=True)

    file_path = os.path.join(knowledge_dir, file.filename)
    file.save(file_path)

    # 提取文本并入库
    try:
        processor = get_knowledge_processor()

        if ext == "docx":
            text = processor.extract_text_from_docx(file_path)
        elif ext == "xlsx":
            text = processor.extract_text_from_xlsx(file_path, target_spots=["灵山", "灵山胜境", "拈花湾"])
        elif ext == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif ext == "pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text = "\n".join([page.get_text() for page in doc])
            except ImportError:
                return jsonify({"code": 500, "message": "服务器缺少PyMuPDF库，无法解析PDF文件"})
            except Exception as e:
                return jsonify({"code": 500, "message": f"PDF解析失败：{str(e)}"})
        else:
            return jsonify({"code": 400, "message": f"不支持的文件类型：{ext}"})

        if not text.strip():
            os.unlink(file_path)
            return jsonify({"code": 400, "message": "文件中未提取到有效文本内容"})

        # 分割并入库
        chunks = processor.split_text_to_chunks(text, chunk_size=200, overlap=50)
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                "id": f"upload_{file.filename}_{i}",
                "text": chunk,
                "metadata": {
                    "source": f"文件上传: {file.filename}",
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            })

        processor.vector_db.add_documents(documents)

        # 同时在FAQ表中添加一条记录（用于管理展示）
        faq = FaqKnowledge(
            question=f"【文件】{file.filename}",
            answer=text[:500] + ("..." if len(text) > 500 else ""),
            doc_source=file.filename,
            vector_sync=True
        )
        db.session.add(faq)
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": f"文件上传成功，共提取 {len(chunks)} 个文档块",
            "data": {"chunks": len(chunks), "filename": file.filename}
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"文件处理失败：{str(e)}"})


@admin_bp.route("/knowledge/graph", methods=["GET"])
@admin_required
def knowledge_graph():
    """获取知识库图谱数据（节点和边）"""
    try:
        processor = get_knowledge_processor()
        vd = processor.vector_db

        # 1. 获取节点列表（关键词 + FAQ）
        keyword_questions = [
            "灵山大佛", "灵山梵宫", "九龙灌浴", "拈花湾", "佛足坛",
            "门票", "交通", "路线", "表演", "素斋", "住宿",
            "开放时间", "景点", "文化", "历史"
        ]
        nodes = []
        if vd.collection and vd.get_document_count() > 0:
            for kw in keyword_questions:
                results = vd.search(kw, top_k=2)
                for r in results:
                    text = r["text"][:80]
                    nodes.append({
                        "id": f"{kw}_{r['id']}",
                        "label": kw,
                        "text": text,
                        "category": "knowledge"
                    })

        # 去重
        seen = set()
        unique_nodes = []
        for n in nodes:
            key = n["label"]
            if key not in seen:
                seen.add(key)
                unique_nodes.append(n)

        # FAQ节点
        faq_nodes = FaqKnowledge.query.all()
        for faq in faq_nodes:
            if faq.doc_source and faq.doc_source != "手动录入":
                unique_nodes.append({
                    "id": f"faq_{faq.id}",
                    "label": faq.question[:20],
                    "text": faq.answer[:60],
                    "category": "faq"
                })

        # 2. 动态计算语义相似度边（余弦相似度）
        edges = _compute_semantic_edges(unique_nodes)

        # 3. 补充类别边（保留原有的类别关系作为补充）
        category_edges = []
        categories = {
            "景点": ["灵山大佛", "灵山梵宫", "九龙灌浴", "佛足坛", "拈花湾", "曼飞龙塔", "祥符禅寺"],
            "服务": ["门票", "交通", "住宿", "素斋", "表演", "开放时间"],
            "路线": ["路线", "景点", "文化", "历史"]
        }
        for cat, items in categories.items():
            for i in range(len(items) - 1):
                category_edges.append({
                    "source": items[i],
                    "target": items[i + 1],
                    "category": cat,
                    "label": cat
                })

        # 合并边（去重）
        edge_keys = set()
        all_edges = []
        for e in category_edges + edges:
            key = tuple(sorted([e["source"], e["target"]]))
            if key not in edge_keys:
                edge_keys.add(key)
                all_edges.append(e)

        return jsonify({
            "code": 200,
            "data": {
                "nodes": unique_nodes,
                "edges": all_edges,
                "doc_count": vd.get_document_count() if vd.collection else 0,
                "faq_count": len(faq_nodes)
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取图谱数据失败：{str(e)}"})


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def _compute_semantic_edges(nodes: List[Dict]) -> List[Dict]:
    """基于语义相似度动态计算节点间的边关系"""
    if len(nodes) < 2:
        return []

    # 构建特征词典（从所有节点的label和text中提取）
    feature_words = set()
    for n in nodes:
        for kw in ["灵山", "大佛", "梵宫", "九龙", "拈花", "门票", "交通", "路线",
                    "表演", "素斋", "住宿", "文化", "历史", "景点", "开放", "时间",
                    "佛足坛", "曼飞", "祥符", "精舍", "百子", "弥勒", "抱佛",
                    "禅意", "佛教", "太湖", "无锡", "景区", "游览", "攻略",
                    "推荐", "预约", "停车", "优惠", "价格", "门票"]:
            if kw in n["label"] or kw in n["text"]:
                feature_words.add(kw)

    if not feature_words:
        feature_words = ["灵山", "大佛", "梵宫", "门票", "交通", "路线"]

    feature_words = list(feature_words)
    SIMILARITY_THRESHOLD = 0.35  # 相似度阈值

    edges = []

    # 对每个节点计算embedding
    node_vectors = {}
    for n in nodes:
        label = n["label"]
        text = n.get("text", "")
        vector = [0.0] * len(feature_words)
        for idx, feat in enumerate(feature_words):
            vector[idx] = label.count(feat) + text.count(feat)
        node_vectors[n["label"]] = vector

    # 计算节点间相似度
    processed_pairs = set()
    for i, n1 in enumerate(nodes):
        for j, n2 in enumerate(nodes):
            if i >= j:
                continue
            label1, label2 = n1["label"], n2["label"]
            pair_key = tuple(sorted([label1, label2]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)

            sim = _cosine_similarity(node_vectors[label1], node_vectors[label2])

            if sim >= SIMILARITY_THRESHOLD:
                # 根据节点类别判断边的类别
                if n1.get("category") == "faq" or n2.get("category") == "faq":
                    edge_cat = "FAQ"
                elif n1.get("category") == "knowledge" and n2.get("category") == "knowledge":
                    # 景点类知识
                    if any(kw in label1 + label2 for kw in ["大佛", "梵宫", "九龙", "拈花", "坛城"]):
                        edge_cat = "景点"
                    elif any(kw in label1 + label2 for kw in ["门票", "交通", "住宿", "素斋", "表演"]):
                        edge_cat = "服务"
                    elif any(kw in label1 + label2 for kw in ["路线", "文化", "历史", "景点"]):
                        edge_cat = "路线"
                    else:
                        edge_cat = "知识"
                else:
                    edge_cat = "知识"

                edges.append({
                    "source": label1,
                    "target": label2,
                    "category": edge_cat,
                    "label": f"sim:{sim:.2f}",
                    "similarity": round(sim, 3)
                })

    # 按相似度排序，保留Top 50条边
    edges.sort(key=lambda x: x["similarity"], reverse=True)
    return edges[:50]


@admin_bp.route("/knowledge/stats", methods=["GET"])
@admin_required
def knowledge_stats():
    """获取知识库统计信息"""
    try:
        processor = get_knowledge_processor()
        vd = processor.vector_db
        faq_count = FaqKnowledge.query.count()
        doc_count = vd.get_document_count() if vd.collection else 0

        return jsonify({
            "code": 200,
            "data": {
                "vector_doc_count": doc_count,
                "faq_count": faq_count,
                "vector_sync_count": FaqKnowledge.query.filter_by(vector_sync=True).count()
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"统计失败：{str(e)}"})


# ======================== 6. 对话日志管理 ========================
@admin_bp.route("/chat-logs", methods=["GET"])
@admin_required
def list_chat_logs():
    """获取对话日志列表（支持分页、筛选、时间检索）"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    keyword = request.args.get("keyword", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = ChatLog.query

    if keyword:
        query = query.filter(
            ChatLog.question_text.contains(keyword) |
            ChatLog.answer_text.contains(keyword)
        )

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(ChatLog.question_time >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(ChatLog.question_time < dt_to)
        except ValueError:
            pass

    pagination = query.order_by(ChatLog.question_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "code": 200,
        "data": {
            "items": [log.to_dict() for log in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages
        }
    })


@admin_bp.route("/chat-logs/export", methods=["GET"])
@admin_required
def export_chat_logs():
    """批量导出对话日志为Excel文件"""
    keyword = request.args.get("keyword", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = ChatLog.query

    if keyword:
        query = query.filter(
            ChatLog.question_text.contains(keyword) |
            ChatLog.answer_text.contains(keyword)
        )

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(ChatLog.question_time >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(ChatLog.question_time < dt_to)
        except ValueError:
            pass

    logs = query.order_by(ChatLog.question_time.desc()).all()

    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "对话日志"

        # 表头
        headers = ["ID", "用户ID", "提问内容", "AI回答", "提问时间", "情绪标签", "语音时长", "数字人ID", "音色"]
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        # 数据行
        for row_idx, log in enumerate(logs, 2):
            ws.cell(row=row_idx, column=1, value=log.id)
            ws.cell(row=row_idx, column=2, value=log.user_id)
            ws.cell(row=row_idx, column=3, value=log.question_text)
            ws.cell(row=row_idx, column=4, value=log.answer_text)
            ws.cell(row=row_idx, column=5, value=log.question_time.strftime("%Y-%m-%d %H:%M:%S"))
            ws.cell(row=row_idx, column=6, value=log.emotion_label)
            ws.cell(row=row_idx, column=7, value=log.voice_duration)
            ws.cell(row=row_idx, column=8, value=log.digital_human_id)
            ws.cell(row=row_idx, column=9, value=log.tts_voice)

        # 调整列宽
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 40
        ws.column_dimensions["D"].width = 60
        ws.column_dimensions["E"].width = 20
        ws.column_dimensions["F"].width = 12
        ws.column_dimensions["G"].width = 12
        ws.column_dimensions["H"].width = 12
        ws.column_dimensions["I"].width = 25

        # 保存到临时文件
        import tempfile
        tmp_path = os.path.join(tempfile.gettempdir(), f"chat_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(tmp_path)

        # 返回文件下载
        from flask import send_file
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=f"灵山胜境对话日志_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except ImportError:
        return jsonify({"code": 500, "message": "服务器缺少openpyxl库，无法导出Excel"})


# ========================================
# 游客感受度报告 - 降级生成函数
# ========================================

def _generate_default_kw_analysis(top5_kw, satisfaction, total):
    """大模型调用失败时的降级生成：游客关注点分析"""
    if not top5_kw:
        return "暂无游客关注点数据，系统仍在收集中。"

    top1 = top5_kw[0]
    top2 = top5_kw[1] if len(top5_kw) > 1 else top5_kw[0]
    return (
        f"根据近期游客交互数据分析，游客最关注的是「{top1['keyword']}」（{top1['count']}次）和「{top2['keyword']}」（{top2['count']}次）。"
        f"整体满意度为{satisfaction}%，游客主要围绕景区核心景点和服务设施进行咨询，"
        f"建议针对性优化高频问题对应的服务内容和知识库覆盖范围。"
    )


def _generate_default_trend_analysis(emotion_trend):
    """大模型调用失败时的降级生成：情感趋势分析"""
    if not emotion_trend:
        return "近7天情感趋势数据较少，系统仍在收集中。"

    latest = emotion_trend[-1]
    top_emotion = max(latest.get("data", {}), key=latest.get("data", {}).get, default="微笑")
    return (
        f"近7天情感趋势显示，「{top_emotion}」为最常见情感，"
        f"整体情感分布较为稳定。建议持续优化服务体验，保持正面情感占比，"
        f"同时关注负面情感波动，及时调整服务策略。"
    )


def _generate_default_suggestions(keyword_counts, satisfaction, total):
    """大模型调用失败时的降级生成：服务建议"""
    suggestions = []
    if keyword_counts and keyword_counts[0]["count"] > 0:
        top_kw = keyword_counts[0]["keyword"]
        if top_kw == "交通":
            suggestions.append("交通问题咨询较多，建议在首页增加交通指引卡片和公交/自驾路线图")
        elif top_kw == "门票":
            suggestions.append("门票价格咨询频繁，建议增设自动播报入口和优惠政策提醒")
        elif top_kw == "路线":
            suggestions.append("游客对路线规划需求较高，建议优化推荐路线算法，提供定制化游览方案")
        elif top_kw == "大佛":
            suggestions.append("灵山大佛为热门景点，建议增加互动讲解和文化故事推送")
        elif top_kw == "素斋":
            suggestions.append("素斋服务受关注，建议发布素斋菜单和预订信息")
        else:
            suggestions.append(f"「{top_kw}」关注度高，建议针对性优化相关服务")

    if satisfaction < 60:
        suggestions.append(f"游客满意度偏低（{satisfaction}%），建议加强情感识别和问题解决能力，提升服务温度")
    elif satisfaction < 80:
        suggestions.append(f"游客满意度一般（{satisfaction}%），建议优化数字人交互话术，增加个性化服务")

    if not suggestions:
        suggestions.append("当前服务运行良好，游客满意度较高，建议继续保持高质量互动，定期更新知识库内容")

    return suggestions


# ======================== 6. 对话日志导出 ========================
@admin_bp.route("/chat-logs/export", methods=["GET"])
@admin_required
def chat_log_export():
    """导出对话日志为Excel文件"""
    try:
        from sqlalchemy import func
        # 参数
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        keyword = request.args.get("keyword", "")
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")

        query = ChatLog.query

        if keyword:
            query = query.filter(
                ChatLog.question_text.contains(keyword) |
                ChatLog.answer_text.contains(keyword)
            )

        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(ChatLog.question_time >= dt_from)
            except ValueError:
                pass

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(ChatLog.question_time < dt_to)
            except ValueError:
                pass

        logs = query.order_by(ChatLog.question_time.desc()).all()

        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "对话日志"

            # 表头
            headers = ["ID", "用户ID", "提问内容", "AI回答", "提问时间", "情绪标签", "语音时长", "数字人ID", "音色"]
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            # 数据行
            for row_idx, log in enumerate(logs, 2):
                ws.cell(row=row_idx, column=1, value=log.id)
                ws.cell(row=row_idx, column=2, value=log.user_id)
                ws.cell(row=row_idx, column=3, value=log.question_text)
                ws.cell(row=row_idx, column=4, value=log.answer_text)
                ws.cell(row=row_idx, column=5, value=log.question_time.strftime("%Y-%m-%d %H:%M:%S"))
                ws.cell(row=row_idx, column=6, value=log.emotion_label)
                ws.cell(row=row_idx, column=7, value=log.voice_duration)
                ws.cell(row=row_idx, column=8, value=log.digital_human_id)
                ws.cell(row=row_idx, column=9, value=log.tts_voice)

            # 调整列宽
            ws.column_dimensions["A"].width = 8
            ws.column_dimensions["B"].width = 10
            ws.column_dimensions["C"].width = 40
            ws.column_dimensions["D"].width = 60
            ws.column_dimensions["E"].width = 20
            ws.column_dimensions["F"].width = 12
            ws.column_dimensions["G"].width = 12
            ws.column_dimensions["H"].width = 12
            ws.column_dimensions["I"].width = 25

            # 保存到临时文件
            import tempfile
            tmp_path = os.path.join(tempfile.gettempdir(), f"chat_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            wb.save(tmp_path)

            # 返回文件下载
            from flask import send_file
            return send_file(
                tmp_path,
                as_attachment=True,
                download_name=f"灵山胜境对话日志_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except ImportError:
            return jsonify({"code": 500, "message": "服务器缺少openpyxl库，无法导出Excel"})

    except Exception as e:
        return jsonify({"code": 500, "message": f"导出失败：{str(e)}"})


# ========================================
# 游客感受度报告 - 降级生成函数（大模型不可用时使用）
# ========================================

def _generate_default_kw_analysis(top5_kw, satisfaction, total):
    """大模型调用失败时的降级生成：游客关注点分析"""
    if not top5_kw:
        return "暂无游客关注点数据，系统仍在收集中。"

    top1 = top5_kw[0]
    top2 = top5_kw[1] if len(top5_kw) > 1 else top5_kw[0]
    return (
        f"根据近期游客交互数据分析，游客最关注的是「{top1['keyword']}」（{top1['count']}次）和「{top2['keyword']}」（{top2['count']}次）。"
        f"整体满意度为{satisfaction}%，游客主要围绕景区核心景点和服务设施进行咨询，"
        f"建议针对性优化高频问题对应的服务内容和知识库覆盖范围。"
    )


def _generate_default_trend_analysis(emotion_trend):
    """大模型调用失败时的降级生成：情感趋势分析"""
    if not emotion_trend:
        return "近7天情感趋势数据较少，系统仍在收集中。"

    latest = emotion_trend[-1]
    top_emotion = max(latest.get("data", {}), key=latest.get("data", {}).get, default="微笑")
    return (
        f"近7天情感趋势显示，「{top_emotion}」为最常见情感，"
        f"整体情感分布较为稳定。建议持续优化服务体验，保持正面情感占比，"
        f"同时关注负面情感波动，及时调整服务策略。"
    )


def _generate_default_suggestions(keyword_counts, satisfaction, total):
    """大模型调用失败时的降级生成：服务建议"""
    suggestions = []
    if keyword_counts and keyword_counts[0]["count"] > 0:
        top_kw = keyword_counts[0]["keyword"]
        if top_kw == "交通":
            suggestions.append("交通问题咨询较多，建议在首页增加交通指引卡片和公交/自驾路线图")
        elif top_kw == "门票":
            suggestions.append("门票价格咨询频繁，建议增设自动播报入口和优惠政策提醒")
        elif top_kw == "路线":
            suggestions.append("游客对路线规划需求较高，建议优化推荐路线算法，提供定制化游览方案")
        elif top_kw == "大佛":
            suggestions.append("灵山大佛为热门景点，建议增加互动讲解和文化故事推送")
        elif top_kw == "素斋":
            suggestions.append("素斋服务受关注，建议发布素斋菜单和预订信息")
        else:
            suggestions.append(f"「{top_kw}」关注度高，建议针对性优化相关服务")

    if satisfaction < 60:
        suggestions.append(f"游客满意度偏低（{satisfaction}%），建议加强情感识别和问题解决能力，提升服务温度")
    elif satisfaction < 80:
        suggestions.append(f"游客满意度一般（{satisfaction}%），建议优化数字人交互话术，增加个性化服务")

    if not suggestions:
        suggestions.append("当前服务运行良好，游客满意度较高，建议继续保持高质量互动，定期更新知识库内容")

    return suggestions


# ======================== 7. 数据大屏统计 ========================
@admin_bp.route("/dashboard/stats", methods=["GET"])
@admin_required
def dashboard_stats():
    """获取数据大屏统计信息"""
    try:
        # 总对话数
        total_chats = ChatLog.query.count()
        # 总用户数
        total_users = User.query.count()
        # 今日对话数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_chats = ChatLog.query.filter(ChatLog.question_time >= today_start).count()
        # 知识库条目数
        total_knowledge = FaqKnowledge.query.count()
        # 数字人数
        total_digital_humans = DigitalHuman.query.count()

        # 热门问题TOP10
        from sqlalchemy import func
        hot_questions = db.session.query(
            ChatLog.question_text,
            func.count(ChatLog.id).label("count")
        ).group_by(ChatLog.question_text).order_by(
            func.count(ChatLog.id).desc()
        ).limit(10).all()

        # 情绪分布
        emotion_stats = db.session.query(
            ChatLog.emotion_label,
            func.count(ChatLog.id).label("count")
        ).group_by(ChatLog.emotion_label).all()

        # 近7天对话趋势
        seven_days_ago = today_start - timedelta(days=6)
        daily_chats = db.session.query(
            func.date(ChatLog.question_time).label("date"),
            func.count(ChatLog.id).label("count")
        ).filter(ChatLog.question_time >= seven_days_ago).group_by(
            func.date(ChatLog.question_time)
        ).order_by(func.date(ChatLog.question_time)).all()

        return jsonify({
            "code": 200,
            "data": {
                "total_chats": total_chats,
                "total_users": total_users,
                "today_chats": today_chats,
                "total_knowledge": total_knowledge,
                "total_digital_humans": total_digital_humans,
                "hot_questions": [
                    {"question": q[0][:50] + "..." if len(q[0]) > 50 else q[0], "count": q[1]}
                    for q in hot_questions
                ],
                "emotion_stats": {e[0]: e[1] for e in emotion_stats},
                "daily_chats": [
                    {"date": d[0], "count": d[1]} for d in daily_chats
                ]
            }
        })
    except Exception as e:
        print(f"[Dashboard] 统计失败：{e}")
        return jsonify({"code": 500, "message": f"统计失败：{str(e)}"})


# ======================== 8. AI参数配置 ========================
@admin_bp.route("/ai-config", methods=["GET"])
@admin_required
def get_ai_config():
    """获取当前AI配置"""
    llm = get_llm_service()
    return jsonify({
        "code": 200,
        "data": llm.get_config()
    })


@admin_bp.route("/ai-config", methods=["PUT"])
@admin_required
def update_ai_config():
    """更新AI配置"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数不能为空"})

    llm = get_llm_service()
    llm.update_config(
        api_key=data.get("api_key"),
        api_base=data.get("api_base"),
        model_name=data.get("model_name"),
        vision_model=data.get("vision_model")
    )

    return jsonify({
        "code": 200,
        "message": "AI配置更新成功，全局生效",
        "data": llm.get_config()
    })


@admin_bp.route("/emotion/report", methods=["GET"])
@admin_required
def emotion_report():
    """游客感受度报告 - 返回结构化数据"""
    try:
        from sqlalchemy import func
        from services.llm_service import get_llm_service

        llm = get_llm_service()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=6)

        # 情感统计
        emotion_stats = db.session.query(
            ChatLog.emotion_label,
            func.count(ChatLog.id).label("count")
        ).group_by(ChatLog.emotion_label).all()
        emotion_dict = {e[0]: e[1] for e in emotion_stats}

        # 今日情感统计
        today_emotion = db.session.query(
            ChatLog.emotion_label,
            func.count(ChatLog.id).label("count")
        ).filter(ChatLog.question_time >= today_start).group_by(ChatLog.emotion_label).all()
        today_emotion_dict = {e[0]: e[1] for e in today_emotion}

        # 近7天情感趋势（按日期+情感聚合）
        emotion_trend_raw = db.session.query(
            func.date(ChatLog.question_time).label("date"),
            ChatLog.emotion_label,
            func.count(ChatLog.id).label("count")
        ).filter(ChatLog.question_time >= seven_days_ago).group_by(
            func.date(ChatLog.question_time), ChatLog.emotion_label
        ).order_by(func.date(ChatLog.question_time)).all()

        # 整理趋势数据：{日期: {情感1: count, 情感2: count, ...}}
        trend_data = {}
        emotion_types = list(emotion_dict.keys())
        for row in emotion_trend_raw:
            date_str = row[0]
            if date_str not in trend_data:
                trend_data[date_str] = {e: 0 for e in emotion_types}
            trend_data[date_str][row[1]] = row[2]

        # 补充缺失日期的数据
        all_dates = []
        current = seven_days_ago
        while current <= today_start:
            date_str = current.strftime("%Y-%m-%d")
            all_dates.append(date_str)
            if date_str not in trend_data:
                trend_data[date_str] = {e: 0 for e in emotion_types}
            current += timedelta(days=1)

        # 按日期整理趋势
        emotion_trend = []
        for date_str in all_dates:
            emotion_trend.append({
                "date": date_str,
                "data": trend_data.get(date_str, {})
            })

        # 游客关注点分析（高频问题聚类）
        keywords = ["门票", "交通", "路线", "景点", "表演", "素斋", "住宿", "大佛", "梵宫", "拈花湾"]
        keyword_counts = []
        for kw in keywords:
            count = db.session.query(func.count(ChatLog.id)).filter(
                ChatLog.question_text.contains(kw)
            ).scalar() or 0
            keyword_counts.append({"keyword": kw, "count": count})
        keyword_counts.sort(key=lambda x: x["count"], reverse=True)

        # 满意度估算（基于情感标签）
        positive_labels = ["微笑", "热情", "开心"]
        negative_labels = ["平静", "困惑", "不满"]
        total = ChatLog.query.count()
        positive = ChatLog.query.filter(ChatLog.emotion_label.in_(positive_labels)).count()
        negative = ChatLog.query.filter(ChatLog.emotion_label.in_(negative_labels)).count()
        satisfaction = round(positive / total * 100, 1) if total > 0 else 0

        # 使用大模型生成游客关注点分析
        if keyword_counts and total > 0:
            top5_kw = keyword_counts[:5]
            top5_str = "、".join([f"「{kw['keyword']}」（{kw['count']}次）" for kw in top5_kw])
            kw_prompt = f"""你是灵山胜境AI数字人导游系统的数据分析专家。请根据以下游客交互数据，生成一份专业的游客关注点分析报告（150字左右）。

数据概况：
- 总对话次数：{total}次
- 游客关注热点TOP5：{top5_str}
- 满意度：{satisfaction}%

请从游客行为分析的角度，解读这些数据说明了什么，给出有洞察力的分析结论。
格式要求：一段连贯的文字分析，不要分点列表。"""

            try:
                kw_analysis = llm.chat([{"role": "user", "content": kw_prompt}])
                if len(kw_analysis) < 20:
                    kw_analysis = _generate_default_kw_analysis(top5_kw, satisfaction, total)
            except Exception:
                kw_analysis = _generate_default_kw_analysis(top5_kw, satisfaction, total)
        else:
            kw_analysis = "暂无游客关注点数据，系统仍在收集中。"

        # 使用大模型生成情感趋势分析
        if emotion_trend:
            trend_summary = []
            for item in emotion_trend:
                date_data = item.get("data", {})
                if date_data:
                    top_e = max(date_data, key=date_data.get, default="微笑")
                    count = date_data[top_e]
                    trend_summary.append(f"{item['date']}：「{top_e}」{count}次")
            trend_str = "；".join(trend_summary)

            trend_prompt = f"""你是灵山胜境AI数字人导游系统的情感分析师。请根据近7天游客情感趋势数据，生成一份专业的趋势分析报告（120字左右）。

近7天情感趋势：
{trend_str}

请分析情感的整体走势、变化规律，以及这些数据对服务质量管理的启示。
格式要求：一段连贯的文字分析，不要分点列表。"""

            try:
                trend_analysis = llm.chat([{"role": "user", "content": trend_prompt}])
                if len(trend_analysis) < 20:
                    trend_analysis = _generate_default_trend_analysis(emotion_trend)
            except Exception:
                trend_analysis = _generate_default_trend_analysis(emotion_trend)
        else:
            trend_analysis = "近7天情感趋势数据较少，系统仍在收集中。"

        # 使用大模型生成服务建议
        top3_keywords_str = "、".join([f"「{kw['keyword']}」" for kw in keyword_counts[:3]])

        suggestions_prompt = f"""你是灵山胜境AI数字人导游系统的运营顾问。请根据以下数据分析结果，给出3-5条切实可行的服务优化建议。

数据摘要：
- 总对话数：{total}次
- 满意度：{satisfaction}%
- 正面情感占比：{(positive/total*100):.1f}%  负面情感占比：{(negative/total*100):.1f}%
- 游客关注热点TOP3：{top3_keywords_str}

请给出具体可执行的建议，每条建议50字以内。
格式要求：每条建议单独一行，前缀为"• "。"""

        try:
            suggestions_raw = llm.chat([{"role": "user", "content": suggestions_prompt}])
            suggestions = [s.strip("• ") for s in suggestions_raw.strip().split("\n") if s.strip()]
            if len(suggestions) < 1:
                suggestions = _generate_default_suggestions(keyword_counts, satisfaction, total)
        except Exception:
            suggestions = _generate_default_suggestions(keyword_counts, satisfaction, total)

        return jsonify({
            "code": 200,
            "data": {
                "emotion_stats": emotion_dict,
                "today_emotion": today_emotion_dict,
                "emotion_trend": emotion_trend,
                "keyword_counts": keyword_counts,
                "satisfaction": satisfaction,
                "total_chats": total,
                "kw_analysis": kw_analysis,
                "trend_analysis": trend_analysis,
                "suggestions": suggestions
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"报告生成失败：{str(e)}"})


@admin_bp.route("/dashboard/pref", methods=["GET"])
@admin_required
def dashboard_pref():
    """获取游览偏好数据（数据大屏用）"""
    try:
        from sqlalchemy import func
        # 数字人使用统计
        dh_stats = db.session.query(
            ChatLog.digital_human_id,
            DigitalHuman.name,
            func.count(ChatLog.id).label("count")
        ).join(DigitalHuman, ChatLog.digital_human_id == DigitalHuman.id).group_by(
            ChatLog.digital_human_id, DigitalHuman.name
        ).order_by(func.count(ChatLog.id).desc()).all()

        # 音色使用统计
        voice_stats = db.session.query(
            ChatLog.tts_voice,
            func.count(ChatLog.id).label("count")
        ).group_by(ChatLog.tts_voice).order_by(func.count(ChatLog.id).desc()).limit(5).all()

        return jsonify({
            "code": 200,
            "data": {
                "digital_humans": [{"name": d[1], "count": d[2]} for d in dh_stats],
                "voices": [{"voice": v[0], "count": v[1]} for v in voice_stats]
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"数据获取失败：{str(e)}"})
