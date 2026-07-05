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
from models import db, Admin, User, ChatLog, FaqKnowledge, DigitalHuman, Knowledge, KnowledgeCategory, KnowledgeVersion
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


# ======================== 4b. 扫描 LiveTalking 已生成的 Avatar ========================
@admin_bp.route("/digital-humans/avatars-on-disk", methods=["GET"])
@admin_required
def list_avatars_on_disk():
    """扫描 LiveTalking data/avatars/ 目录，返回所有可用的 avatar 文件夹"""
    import os
    avatars_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'LiveTalking', 'data', 'avatars'
    )
    result = []
    if os.path.isdir(avatars_dir):
        for name in sorted(os.listdir(avatars_dir)):
            full = os.path.join(avatars_dir, name)
            if not os.path.isdir(full):
                continue
            # 检查是否是有效 avatar（有 coords.pkl 或 latents.pt）
            has_coords = os.path.isfile(os.path.join(full, 'coords.pkl'))
            has_latents = os.path.isfile(os.path.join(full, 'latents.pt'))
            has_imgs = os.path.isdir(os.path.join(full, 'full_imgs'))
            if has_coords or has_latents or has_imgs:
                result.append({
                    'folder': name,
                    'has_coords': has_coords,
                    'has_latents': has_latents,
                    'has_imgs': has_imgs,
                })
    return jsonify({"code": 200, "data": result})


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
    """一键同步知识库到向量库（文档目录 + FAQ表 + 通用知识库）"""
    try:
        processor = get_knowledge_processor()

        # 1. 同步文档目录
        doc_count = processor.build_knowledge_base()

        # 2. 同步FAQ表中的知识（未同步的条目）
        unsynced_faq = FaqKnowledge.query.filter_by(vector_sync=False).all()
        faq_docs = []
        for faq in unsynced_faq:
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
        FaqKnowledge.query.update({FaqKnowledge.vector_sync: True})

        # 3. 同步通用知识库（未同步的条目）
        unsynced_knowledge = Knowledge.query.filter_by(vector_sync=False, is_active=True).all()
        knowledge_docs = []
        for k in unsynced_knowledge:
            knowledge_docs.append({
                "id": f"knowledge_{k.id}",
                "text": f"标题：{k.title}\n内容：{k.content}",
                "metadata": {
                    "source": k.category.name if k.category else "未知",
                    "type": k.category.code if k.category else "unknown",
                    "id": k.id
                }
            })

        if knowledge_docs:
            processor.vector_db.add_documents(knowledge_docs)
        Knowledge.query.filter_by(vector_sync=False, is_active=True).update({Knowledge.vector_sync: True})
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": f"向量库同步完成，文档{doc_count}条 + FAQ{len(faq_docs)}条 + 知识库{len(knowledge_docs)}条",
            "data": {"doc_count": doc_count, "faq_count": len(faq_docs), "knowledge_count": len(knowledge_docs)}
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

        # 自动检测知识类型
        detected_type = "faq"
        scene_keywords = ["景点", "讲解", "介绍", "景观", "建筑", "佛像", "大佛", "梵宫"]
        history_keywords = ["历史", "文化", "古代", "朝代", "佛教", "传统", "习俗", "典故"]
        info_keywords = ["门票", "交通", "停车", "开放时间", "价格", "门票价格", "游玩时间"]
        route_keywords = ["路线", "行程", "攻略", "游览", "推荐路线", "游玩顺序"]

        text_lower = text.lower()
        scores = {
            "faq": sum(1 for q in ["如何", "怎么", "什么", "吗", "?", "？"] if q in text_lower),
            "scene_intro": sum(1 for kw in scene_keywords if kw in text_lower),
            "history": sum(1 for kw in history_keywords if kw in text_lower),
            "basic_info": sum(1 for kw in info_keywords if kw in text_lower),
            "route": sum(1 for kw in route_keywords if kw in text_lower),
        }
        detected_type = max(scores, key=scores.get)
        category_map = {
            "faq": "faq", "scene_intro": "scene_intro",
            "history": "history", "basic_info": "basic_info", "route": "route"
        }

        # 在通用知识库中创建记录
        cat = KnowledgeCategory.query.filter_by(code=category_map.get(detected_type, "faq")).first()
        if cat:
            keywords = _extract_keywords(text, top_k=8)
            knowledge = Knowledge(
                category_id=cat.id,
                title=f"【文件】{file.filename}",
                content=text[:2000] + ("..." if len(text) > 2000 else ""),
                tags=", ".join(keywords),
                source_file=file.filename,
                keywords=", ".join(keywords),
                vector_sync=True,
                is_active=True
            )
            db.session.add(knowledge)

        # 同时在FAQ表中添加一条记录（保持兼容）
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
            "message": f"文件上传成功，共提取 {len(chunks)} 个文档块，检测到类型: {detected_type}",
            "data": {"chunks": len(chunks), "filename": file.filename, "detected_type": detected_type}
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
        knowledge_count = Knowledge.query.filter_by(is_active=True).count()
        category_count = KnowledgeCategory.query.filter_by(is_active=True).count()

        # 按分类统计
        category_stats = {}
        for cat in KnowledgeCategory.query.filter_by(is_active=True).all():
            count = Knowledge.query.filter_by(category_id=cat.id, is_active=True).count()
            category_stats[cat.code] = {"name": cat.name, "count": count}

        return jsonify({
            "code": 200,
            "data": {
                "vector_doc_count": doc_count,
                "faq_count": faq_count,
                "vector_sync_count": FaqKnowledge.query.filter_by(vector_sync=True).count(),
                "knowledge_count": knowledge_count,
                "category_count": category_count,
                "category_stats": category_stats
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"统计失败：{str(e)}"})


# ======================== 知识库分类管理 ========================
@admin_bp.route("/knowledge/categories", methods=["GET"])
@admin_required
def list_categories():
    """获取知识分类列表"""
    categories = KnowledgeCategory.query.filter_by(is_active=True).order_by(KnowledgeCategory.sort_order).all()
    return jsonify({
        "code": 200,
        "data": [c.to_dict() for c in categories]
    })


@admin_bp.route("/knowledge/categories", methods=["POST"])
@admin_required
def create_category():
    """创建知识分类"""
    data = request.get_json()
    if not data or not data.get("name") or not data.get("code"):
        return jsonify({"code": 400, "message": "分类名称和编码不能为空"})

    existing = KnowledgeCategory.query.filter_by(code=data["code"]).first()
    if existing:
        return jsonify({"code": 400, "message": "分类编码已存在"})

    cat = KnowledgeCategory(
        name=data["name"],
        code=data["code"],
        description=data.get("description", ""),
        icon=data.get("icon", ""),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True)
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify({"code": 200, "message": "创建成功", "data": cat.to_dict()})


@admin_bp.route("/knowledge/categories/<int:cat_id>", methods=["PUT"])
@admin_required
def update_category(cat_id):
    """更新知识分类"""
    cat = KnowledgeCategory.query.get(cat_id)
    if not cat:
        return jsonify({"code": 404, "message": "分类不存在"})

    data = request.get_json()
    if data.get("name") is not None:
        cat.name = data["name"]
    if data.get("description") is not None:
        cat.description = data["description"]
    if data.get("icon") is not None:
        cat.icon = data["icon"]
    if data.get("sort_order") is not None:
        cat.sort_order = data["sort_order"]
    if data.get("is_active") is not None:
        cat.is_active = data["is_active"]

    db.session.commit()
    return jsonify({"code": 200, "message": "更新成功", "data": cat.to_dict()})


@admin_bp.route("/knowledge/categories/<int:cat_id>", methods=["DELETE"])
@admin_required
def delete_category(cat_id):
    """删除知识分类"""
    cat = KnowledgeCategory.query.get(cat_id)
    if not cat:
        return jsonify({"code": 404, "message": "分类不存在"})

    # 检查是否有关联的知识条目
    count = Knowledge.query.filter_by(category_id=cat_id).count()
    if count > 0:
        return jsonify({"code": 400, "message": f"该分类下还有 {count} 条知识内容，请先迁移或删除"})

    db.session.delete(cat)
    db.session.commit()
    return jsonify({"code": 200, "message": "删除成功"})


# ======================== 通用知识库管理 ========================
@admin_bp.route("/knowledge/list", methods=["GET"])
@admin_required
def list_knowledge_v2():
    """获取知识库列表（新版，合并展示 knowledge 表 + faq_knowledge 表）"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # 筛选条件
    category = request.args.get("category", "")        # 分类编码
    keyword = request.args.get("keyword", "")           # 关键词搜索
    tags = request.args.get("tags", "")                 # 标签筛选
    is_active = request.args.get("is_active")           # 状态筛选
    sort_by = request.args.get("sort_by", "created_at") # 排序字段
    sort_order = request.args.get("sort_order", "desc")  # 排序方向

    # ========== 1. 查询新 knowledge 表 ==========
    new_query = Knowledge.query
    if category:
        cat = KnowledgeCategory.query.filter_by(code=category).first()
        if cat:
            new_query = new_query.filter_by(category_id=cat.id)
        else:
            new_query = new_query.filter_by(category_id=-1)
    if keyword:
        new_query = new_query.filter(
            db.or_(
                Knowledge.title.contains(keyword),
                Knowledge.content.contains(keyword),
                Knowledge.tags.contains(keyword),
                Knowledge.keywords.contains(keyword)
            )
        )
    if tags:
        new_query = new_query.filter(Knowledge.tags.contains(tags))
    if is_active and is_active.strip():
        if is_active.lower() in ("true", "1", "yes"):
            new_query = new_query.filter_by(is_active=True)
        else:
            new_query = new_query.filter_by(is_active=False)

    # ========== 2. 查询旧 faq_knowledge 表 ==========
    old_query = FaqKnowledge.query
    if category:
        if category == "faq":
            pass  # 不过滤
        else:
            old_query = old_query.filter_by(id=-1)  # 排除
    if keyword:
        old_query = old_query.filter(FaqKnowledge.question.contains(keyword) | FaqKnowledge.answer.contains(keyword))

    # 获取所有 knowledge 表的标题，用于去重（已迁移的 FAQ 不再展示）
    existing_titles = set(k[0] for k in Knowledge.query.with_entities(Knowledge.title).all())

    # ========== 3. 合并结果为统一格式 ==========
    items = []

    # 新表
    for k in new_query.all():
        items.append({
            "id": k.id,
            "source": "knowledge",
            "category_id": k.category_id,
            "category": k.category.to_dict() if k.category else None,
            "title": k.title,
            "content": k.content,
            "tags": k.tags,
            "source_file": k.source_file or "",
            "keywords": k.keywords,
            "version": k.version,
            "vector_sync": k.vector_sync,
            "is_active": k.is_active,
            "sort_order": k.sort_order,
            "created_at": k.created_at,
            "updated_at": k.updated_at,
        })

    # 旧表 — 兼容展示（跳过已迁移的条目）
    faq_cat = KnowledgeCategory.query.filter_by(code="faq").first()
    faq_cat_dict = faq_cat.to_dict() if faq_cat else None
    for f in old_query.all():
        # 去重：如果该 FAQ 问题已存在于 knowledge 表中，跳过
        if f.question and f.question.strip() in existing_titles:
            continue
        items.append({
            "id": f.id,
            "source": "faq",
            "category_id": faq_cat.id if faq_cat else None,
            "category": faq_cat_dict,
            "title": f.question,
            "content": f.answer,
            "tags": "",
            "source_file": f.doc_source or "手动录入",
            "keywords": "",
            "version": 1,
            "vector_sync": f.vector_sync,
            "is_active": True,
            "sort_order": 0,
            "created_at": f.created_at,
            "updated_at": f.created_at,
        })

    # ========== 4. 排序 ==========
    DATETIME_FIELDS = {"created_at", "updated_at"}

    def get_sort_key(item):
        val = item.get(sort_by)
        if val is None:
            return datetime.min if sort_by in DATETIME_FIELDS else ""
        return val

    if sort_order.lower() == "asc":
        items.sort(key=get_sort_key)
    else:
        items.sort(key=get_sort_key, reverse=True)

    # ========== 5. 手动分页 ==========
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]

    # 格式化时间
    for item in page_items:
        item["created_at"] = item["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        item["updated_at"] = item["updated_at"].strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "code": 200,
        "data": {
            "items": page_items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    })


@admin_bp.route("/knowledge/item", methods=["POST"])
@admin_required
def create_knowledge_v2():
    """创建知识条目（新版）"""
    data = request.get_json()
    if not data or not data.get("title") or not data.get("content"):
        return jsonify({"code": 400, "message": "标题和内容不能为空"})

    # 获取分类
    category_id = data.get("category_id")
    if not category_id:
        return jsonify({"code": 400, "message": "请选择知识分类"})

    cat = KnowledgeCategory.query.get(category_id)
    if not cat:
        return jsonify({"code": 404, "message": "知识分类不存在"})

    knowledge = Knowledge(
        category_id=category_id,
        title=data["title"],
        content=data["content"],
        tags=data.get("tags", ""),
        source_file=data.get("source_file", ""),
        keywords=data.get("keywords", ""),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True)
    )
    db.session.add(knowledge)
    db.session.commit()

    # 自动添加到向量库
    try:
        processor = get_knowledge_processor()
        processor.vector_db.add_documents([{
            "id": f"knowledge_{knowledge.id}",
            "text": f"标题：{knowledge.title}\n内容：{knowledge.content}",
            "metadata": {"source": cat.name, "type": cat.code, "id": knowledge.id}
        }])
        knowledge.vector_sync = True
        db.session.commit()
    except Exception as e:
        print(f"[Warning] 向量库自动同步失败：{e}")

    return jsonify({"code": 200, "message": "创建成功", "data": knowledge.to_dict()})


@admin_bp.route("/knowledge/item/<int:k_id>", methods=["PUT"])
@admin_required
def update_knowledge_v2(k_id):
    """更新知识条目（新版，带版本控制）"""
    knowledge = Knowledge.query.get(k_id)
    if not knowledge:
        return jsonify({"code": 404, "message": "知识条目不存在"})

    data = request.get_json()

    # 保存版本历史
    version_record = KnowledgeVersion(
        knowledge_id=knowledge.id,
        version=knowledge.version,
        title=knowledge.title,
        content=knowledge.content,
        tags=knowledge.tags,
        keywords=knowledge.keywords
    )
    db.session.add(version_record)

    # 更新字段
    if data.get("category_id") is not None:
        knowledge.category_id = data["category_id"]
    if data.get("title") is not None:
        knowledge.title = data["title"]
    if data.get("content") is not None:
        knowledge.content = data["content"]
    if data.get("tags") is not None:
        knowledge.tags = data["tags"]
    if data.get("keywords") is not None:
        knowledge.keywords = data["keywords"]
    if data.get("sort_order") is not None:
        knowledge.sort_order = data["sort_order"]
    if data.get("is_active") is not None:
        knowledge.is_active = data["is_active"]

    knowledge.version += 1
    knowledge.vector_sync = False  # 标记需要重新同步
    db.session.commit()

    return jsonify({"code": 200, "message": "更新成功", "data": knowledge.to_dict()})


@admin_bp.route("/knowledge/item/<int:k_id>", methods=["DELETE"])
@admin_required
def delete_knowledge_v2(k_id):
    """删除知识条目（新版）"""
    knowledge = Knowledge.query.get(k_id)
    if not knowledge:
        return jsonify({"code": 404, "message": "知识条目不存在"})

    # 同时删除版本历史
    KnowledgeVersion.query.filter_by(knowledge_id=k_id).delete()
    db.session.delete(knowledge)
    db.session.commit()
    return jsonify({"code": 200, "message": "删除成功"})


@admin_bp.route("/knowledge/item/<int:k_id>/versions", methods=["GET"])
@admin_required
def get_knowledge_versions(k_id):
    """获取知识条目的版本历史"""
    knowledge = Knowledge.query.get(k_id)
    if not knowledge:
        return jsonify({"code": 404, "message": "知识条目不存在"})

    versions = KnowledgeVersion.query.filter_by(knowledge_id=k_id).order_by(KnowledgeVersion.version.desc()).all()
    return jsonify({
        "code": 200,
        "data": {
            "current_version": knowledge.version,
            "versions": [v.to_dict() for v in versions]
        }
    })


@admin_bp.route("/knowledge/item/<int:k_id>/restore/<int:version_id>", methods=["POST"])
@admin_required
def restore_knowledge_version(k_id, version_id):
    """恢复到指定版本"""
    knowledge = Knowledge.query.get(k_id)
    if not knowledge:
        return jsonify({"code": 404, "message": "知识条目不存在"})

    version = KnowledgeVersion.query.get(version_id)
    if not version or version.knowledge_id != k_id:
        return jsonify({"code": 404, "message": "版本不存在"})

    # 保存当前版本为历史
    current_record = KnowledgeVersion(
        knowledge_id=knowledge.id,
        version=knowledge.version,
        title=knowledge.title,
        content=knowledge.content,
        tags=knowledge.tags,
        keywords=knowledge.keywords
    )
    db.session.add(current_record)

    # 恢复
    knowledge.title = version.title
    knowledge.content = version.content
    knowledge.tags = version.tags
    knowledge.keywords = version.keywords
    knowledge.version += 1
    knowledge.vector_sync = False
    db.session.commit()

    return jsonify({"code": 200, "message": f"已恢复到版本 v{version.version}", "data": knowledge.to_dict()})


# ======================== 批量操作 ========================
@admin_bp.route("/knowledge/batch/import", methods=["POST"])
@admin_required
def batch_import_knowledge():
    """批量导入知识条目（JSON格式）"""
    data = request.get_json()
    if not data or not isinstance(data.get("items"), list):
        return jsonify({"code": 400, "message": "请提供 items 数组"})

    items = data["items"]
    category_id = data.get("category_id")
    if not category_id:
        return jsonify({"code": 400, "message": "请选择知识分类"})

    cat = KnowledgeCategory.query.get(category_id)
    if not cat:
        return jsonify({"code": 404, "message": "知识分类不存在"})

    created = 0
    failed = 0
    errors = []

    for idx, item in enumerate(items):
        try:
            title = item.get("title", f"条目{idx+1}")
            content = item.get("content", "")
            if not content:
                failed += 1
                errors.append(f"第{idx+1}条：内容不能为空")
                continue

            knowledge = Knowledge(
                category_id=category_id,
                title=title,
                content=content,
                tags=item.get("tags", ""),
                keywords=item.get("keywords", ""),
                is_active=item.get("is_active", True)
            )
            db.session.add(knowledge)
            db.session.flush()
            created += 1
        except Exception as e:
            failed += 1
            errors.append(f"第{idx+1}条：{str(e)}")

    db.session.commit()

    # 批量同步向量库
    if created > 0:
        try:
            processor = get_knowledge_processor()
            batch_docs = []
            for item in items[:created]:
                batch_docs.append({
                    "id": f"knowledge_batch_{idx}",
                    "text": f"标题：{item.get('title', '')}\n内容：{item.get('content', '')}",
                    "metadata": {"source": cat.name, "type": cat.code}
                })
            if batch_docs:
                processor.vector_db.add_documents(batch_docs)
        except Exception as e:
            print(f"[Warning] 批量向量同步失败：{e}")

    return jsonify({
        "code": 200,
        "message": f"批量导入完成：成功{created}条，失败{failed}条",
        "data": {"created": created, "failed": failed, "errors": errors[:10]}
    })


@admin_bp.route("/knowledge/batch/export", methods=["GET"])
@admin_required
def batch_export_knowledge():
    """批量导出知识条目（JSON格式）"""
    category = request.args.get("category", "")
    keyword = request.args.get("keyword", "")

    query = Knowledge.query.filter_by(is_active=True)

    if category:
        cat = KnowledgeCategory.query.filter_by(code=category).first()
        if cat:
            query = query.filter_by(category_id=cat.id)

    if keyword:
        query = query.filter(
            db.or_(
                Knowledge.title.contains(keyword),
                Knowledge.content.contains(keyword)
            )
        )

    items = query.order_by(Knowledge.created_at.desc()).all()
    return jsonify({
        "code": 200,
        "data": {
            "items": [
                {
                    "title": k.title,
                    "content": k.content,
                    "tags": k.tags,
                    "keywords": k.keywords,
                    "source_file": k.source_file,
                    "category": k.category.to_dict() if k.category else None
                }
                for k in items
            ]
        }
    })


@admin_bp.route("/knowledge/batch/delete", methods=["POST"])
@admin_required
def batch_delete_knowledge():
    """批量删除知识条目"""
    data = request.get_json()
    if not data or not isinstance(data.get("ids"), list):
        return jsonify({"code": 400, "message": "请提供 ids 数组"})

    ids = data["ids"]
    deleted = 0
    for k_id in ids:
        k = Knowledge.query.get(k_id)
        if k:
            KnowledgeVersion.query.filter_by(knowledge_id=k_id).delete()
            db.session.delete(k)
            deleted += 1
    db.session.commit()
    return jsonify({"code": 200, "message": f"已删除 {deleted} 条知识", "data": {"deleted": deleted}})


@admin_bp.route("/knowledge/batch/sync", methods=["POST"])
@admin_required
def batch_sync_knowledge():
    """批量同步未同步的知识到向量库"""
    unsynced = Knowledge.query.filter_by(vector_sync=False, is_active=True).all()
    synced = 0

    try:
        processor = get_knowledge_processor()
        for k in unsynced:
            processor.vector_db.add_documents([{
                "id": f"knowledge_{k.id}",
                "text": f"标题：{k.title}\n内容：{k.content}",
                "metadata": {
                    "source": k.category.name if k.category else "未知",
                    "type": k.category.code if k.category else "unknown",
                    "id": k.id
                }
            }])
            k.vector_sync = True
            synced += 1
        db.session.commit()
    except Exception as e:
        return jsonify({"code": 500, "message": f"同步失败：{str(e)}"})

    return jsonify({"code": 200, "message": f"同步完成，共{synced}条", "data": {"synced": synced}})


@admin_bp.route("/knowledge/search", methods=["GET"])
@admin_required
def search_knowledge():
    """多维度搜索知识条目"""
    keyword = request.args.get("keyword", "")
    category = request.args.get("category", "")
    tags = request.args.get("tags", "")

    if not keyword and not category and not tags:
        return jsonify({"code": 400, "message": "至少提供一个搜索条件"})

    query = Knowledge.query.filter_by(is_active=True)

    if keyword:
        query = query.filter(
            db.or_(
                Knowledge.title.contains(keyword),
                Knowledge.content.contains(keyword),
                Knowledge.tags.contains(keyword),
                Knowledge.keywords.contains(keyword)
            )
        )

    if category:
        cat = KnowledgeCategory.query.filter_by(code=category).first()
        if cat:
            query = query.filter_by(category_id=cat.id)

    if tags:
        query = query.filter(Knowledge.tags.contains(tags))

    results = query.order_by(Knowledge.created_at.desc()).limit(50).all()

    return jsonify({
        "code": 200,
        "data": {
            "total": len(results),
            "items": [k.to_dict() for k in results]
        }
    })


@admin_bp.route("/knowledge/detect", methods=["POST"])
@admin_required
def detect_knowledge_type():
    """上传文件后自动检测知识类型并提取关键信息"""
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

    # 保存上传文件
    knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "../knowledge")
    knowledge_dir = os.path.abspath(knowledge_dir)
    os.makedirs(knowledge_dir, exist_ok=True)

    file_path = os.path.join(knowledge_dir, file.filename)
    file.save(file_path)

    # 提取文本
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
            return jsonify({"code": 400, "message": "不支持的文件类型"})

        if not text or len(text) < 10:
            return jsonify({"code": 400, "message": "文件内容为空或过短"})

        # 自动检测类型
        detected_type = "faq"
        suggested_category = "faq"

        scene_keywords = ["景点", "讲解", "介绍", "景观", "建筑", "佛像", "大佛", "梵宫"]
        history_keywords = ["历史", "文化", "古代", "朝代", "佛教", "传统", "习俗", "典故"]
        info_keywords = ["门票", "交通", "停车", "开放时间", "价格", "门票价格", "游玩时间"]
        route_keywords = ["路线", "行程", "攻略", "游览", "推荐路线", "游玩顺序"]

        text_lower = text.lower()
        scores = {
            "faq": sum(1 for q in ["如何", "怎么", "什么", "吗", "?", "？"] if q in text_lower),
            "scene_intro": sum(1 for kw in scene_keywords if kw in text_lower),
            "history": sum(1 for kw in history_keywords if kw in text_lower),
            "basic_info": sum(1 for kw in info_keywords if kw in text_lower),
            "route": sum(1 for kw in route_keywords if kw in text_lower),
        }

        best_type = max(scores, key=scores.get)
        detected_type = best_type
        suggested_category = best_type

        # 提取关键词（前10个高频词）
        keywords = _extract_keywords(text, top_k=10)

        # 截断预览
        preview = text[:500] + ("..." if len(text) > 500 else "")

        return jsonify({
            "code": 200,
            "message": "文件分析完成",
            "data": {
                "filename": file.filename,
                "text_length": len(text),
                "preview": preview,
                "detected_type": detected_type,
                "suggested_category": suggested_category,
                "category_scores": scores,
                "keywords": keywords
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"文件处理失败：{str(e)}"})


def _extract_keywords(text, top_k=10):
    """简单的关键词提取（高频词）"""
    # 分词
    import re
    words = re.findall(r'[\u4e00-\u9fff]+', text)
    # 过滤短词
    words = [w for w in words if len(w) >= 2]
    # 统计词频
    from collections import Counter
    counter = Counter(words)
    # 排除常见停用词
    stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
                 "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
                 "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些", "什么", "怎么",
                 "哪", "谁", "为什么", "因为", "所以", "但是", "如果", "可以", "这样", "那样",
                 "这个", "那个", "这些", "那些", "来", "过", "做", "用", "比", "对", "给",
                 "从", "被", "把", "让", "把", "得", "地", "还", "只", "又", "再", "很",
                 "非常", "已经", "可能", "应该", "不会", "不能", "还是", "或者", "以及"}
    filtered = {w: c for w, c in counter.items() if w not in stopwords}
    return [w for w, _ in Counter(filtered).most_common(top_k)]


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
