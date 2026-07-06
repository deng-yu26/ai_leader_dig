"""
==============================================================
游客用户路由模块
提供游客登录、注册、数字人、路线规划等接口
==============================================================
"""

import os
import sys
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify, session
from models import db, User, DigitalHuman, ChatLog, FaqKnowledge

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


# ======================== 1. 游客注册 ========================
@user_bp.route("/register", methods=["POST"])
def user_register():
    """游客注册"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数不能为空"})

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()

    # 校验参数
    if not username or not password:
        return jsonify({"code": 400, "message": "用户名和密码不能为空"})
    if len(username) < 2 or len(username) > 32:
        return jsonify({"code": 400, "message": "用户名长度为2-32个字符"})
    if len(password) < 6:
        return jsonify({"code": 400, "message": "密码长度不能少于6位"})

    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({"code": 400, "message": "用户名已被注册"})

    # 创建用户
    user = User(username=username, phone=phone, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "code": 200,
        "message": "注册成功",
        "data": {
            "id": user.id,
            "username": user.username
        }
    })


# ======================== 2. 游客登录 ========================
@user_bp.route("/login", methods=["POST"])
def user_login():
    """游客登录"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数不能为空"})

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"code": 400, "message": "用户名和密码不能为空"})

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"code": 401, "message": "用户名或密码错误"})

    # 保存登录态
    session["user_id"] = user.id
    session["username"] = user.username

    return jsonify({
        "code": 200,
        "message": "登录成功",
        "data": user.to_dict()
    })


# ======================== 3. 用户信息 ========================
@user_bp.route("/info", methods=["GET"])
def user_info():
    """获取当前登录用户信息"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"code": 401, "message": "未登录"})

    user = User.query.get(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"code": 401, "message": "用户不存在"})

    return jsonify({"code": 200, "data": user.to_dict()})


# ======================== 4. 获取可用数字人列表 ========================
@user_bp.route("/digital-humans", methods=["GET"])
def get_digital_humans():
    """获取所有已启用的数字人形象"""
    humans = DigitalHuman.query.filter_by(is_active=True).all()
    return jsonify({
        "code": 200,
        "data": [h.to_dict() for h in humans]
    })


# ======================== 5. 智能路线规划 ========================
@user_bp.route("/route-plan", methods=["GET"])
def get_route_plan():
    """获取三套差异化灵山游览路线"""
    route_type = request.args.get("type", "all")  # all/culture/nature/family

    routes = {
        "culture": {
            "title": "文化朝圣路线（3小时精华游）",
            "description": "适合时间有限但想深度体验佛教文化的游客，以灵山胜境核心佛教文化景点为主线。",
            "duration": "约3小时",
            "spots": [
                {"name": "南门（入口）", "description": "从景区南门入园，开启朝圣之旅"},
                {"name": "佛足坛", "description": "参观佛陀足迹石刻，感受佛教文化传承"},
                {"name": "九龙灌浴", "description": "观赏九龙灌浴表演，聆听释迦牟尼诞生故事"},
                {"name": "祥符禅寺", "description": "千年古刹，灵山佛教文化的发源地，感受庄严氛围"},
                {"name": "灵山大佛", "description": "登顶88米大佛，抱佛脚祈福，俯瞰太湖全景"},
                {"name": "梵宫", "description": "欣赏佛教艺术殿堂，观看《吉祥颂》演出"},
                {"name": "五印坛城", "description": "体验藏传佛教文化，欣赏唐卡艺术"}
            ],
            "tips": "建议上午9点前入园，先看九龙灌浴表演，再登大佛"
        },
        "nature": {
            "title": "自然风光路线（5小时全景游）",
            "description": "适合喜欢户外自然风光的游客，融合太湖山水与佛教园林景观。",
            "duration": "约5小时",
            "spots": [
                {"name": "南门（入口）", "description": "从南门入园，开始全景之旅"},
                {"name": "佛足坛", "description": "参观佛陀足迹石刻"},
                {"name": "九龙灌浴", "description": "观赏动态水景表演，接取祈福圣水"},
                {"name": "菩提大道", "description": "漫步菩提大道，欣赏太湖与青龙山、白虎山自然风貌"},
                {"name": "灵山大佛", "description": "登顶俯瞰太湖全景，拍摄绝美日落照片"},
                {"name": "曼飞龙塔", "description": "欣赏傣族佛教建筑风格与园林景观"},
                {"name": "灵山精舍", "description": "体验禅意园林，品尝素斋"},
                {"name": "梵宫广场", "description": "在梵宫广场结束旅程，感受建筑之美"}
            ],
            "tips": "建议上午入园，自带相机，在灵山大佛平台拍摄太湖日落"
        },
        "family": {
            "title": "亲子家庭路线（4小时轻松游）",
            "description": "适合带孩子的家庭游客，互动性强，轻松愉快。",
            "duration": "约4小时",
            "spots": [
                {"name": "南门（入口）", "description": "从南门入园，开启亲子之旅"},
                {"name": "九龙灌浴", "description": "观赏动态表演，听佛陀诞生的故事"},
                {"name": "佛手广场", "description": "摸'天下第一掌'，祈福平安"},
                {"name": "百子戏弥勒", "description": "与形态各异的孩童雕塑互动拍照"},
                {"name": "梵宫", "description": "欣赏色彩缤纷的艺术作品，观看《吉祥颂》"},
                {"name": "五印坛城", "description": "体验藏式文化，转动经筒"}
            ],
            "tips": "参加抱佛脚亲子活动，品尝素面套餐，在百子戏弥勒前拍照留念"
        }
    }

    if route_type != "all" and route_type in routes:
        return jsonify({"code": 200, "data": routes[route_type]})

    return jsonify({"code": 200, "data": routes})


# ======================== 6. 个人对话历史 ========================
@user_bp.route("/chat-history", methods=["GET"])
def get_chat_history():
    """获取对话历史——按会话分组，支持多轮对话展示"""
    user_id = session.get("user_id")
    if not user_id:
        user_id = 0  # 兼容未登录

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    from sqlalchemy import desc
    pagination = ChatLog.query.filter(
        (ChatLog.user_id == user_id) | (ChatLog.user_id == 0)
    ).order_by(desc(ChatLog.question_time))\
     .paginate(page=page, per_page=per_page * 5, error_out=False)

    # 按 session_id 分组
    sessions_map = {}
    ordered = []
    for log in pagination.items:
        sid = log.session_id or f"single_{log.id}"
        if sid not in sessions_map:
            sessions_map[sid] = {
                "session_id": sid,
                "title": log.question_text[:30],
                "time": log.question_time.strftime("%m-%d %H:%M"),
                "emotion": log.emotion_label,
                "message_count": 0,
                "route_data": None,
                "messages": []
            }
            ordered.append(sid)
        s = sessions_map[sid]
        s["message_count"] += 1
        s["messages"].append(log.to_dict())
        if log.route_data and not s["route_data"]:
            try:
                s["route_data"] = json.loads(log.route_data)
            except Exception:
                pass

    sessions = [sessions_map[sid] for sid in ordered]
    total_sessions = len(sessions_map)

    return jsonify({
        "code": 200,
        "data": {
            "sessions": sessions,
            "total": total_sessions,
            "page": page,
            "per_page": per_page
        }
    })


# ======================== 7. 获取WebSocket连接信息 ========================
@user_bp.route("/ws-info", methods=["GET"])
def get_ws_info():
    """获取WebSocket连接地址和参数"""
    ws_protocol = "wss" if request.is_secure else "ws"

    return jsonify({
        "code": 200,
        "data": {
            "ws_url": f"{ws_protocol}://{request.host}/ws/chat",
            "user_id": session.get("user_id", 0),
            "map_key": "d4aa073ce5b461a2fbfbf97b2b16fd3d"
        }
    })
