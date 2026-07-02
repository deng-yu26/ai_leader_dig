"""
==============================================================
【灵山胜境AI数字人导游系统】Flask主应用入口
==============================================================
"""

import os
import sys

# 确保项目目录在路径中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_sock import Sock

# 导入配置
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    UPLOAD_FOLDER
)

# 导入数据库模型
from models import db

# 导入路由
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp

# 导入WebSocket
from websocket.chat_ws import register_websocket

# 导入RAG服务
from services.rag_service import get_knowledge_processor


def _auto_build_knowledge_base():
    """启动时自动构建向量库（如果为空）"""
    rag = get_knowledge_processor()
    count = rag.get_document_count()
    if count == 0:
        print("\n[RAG] 向量库为空，正在自动构建知识库...")
        count = rag.build_knowledge_base()
        print(f"[RAG] 知识库自动构建完成，共入库 {count} 个文档块\n")
    else:
        print(f"\n[RAG] 知识库已就绪，共 {count} 个文档块\n")


def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)

    # ===== 基础配置 =====
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
    app.config["SESSION_TYPE"] = "filesystem"  # 文件系统存储session

    # ===== 跨域配置 =====
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})

    # ===== 初始化数据库 =====
    db.init_app(app)

    # ===== 注册蓝图 =====
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    # ===== 注册WebSocket =====
    sock = Sock(app)
    register_websocket(app, sock)

    # ===== 静态文件服务 =====
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        """提供上传文件的访问"""
        return send_from_directory(UPLOAD_FOLDER, filename)

    # ===== 健康检查 =====
    @app.route("/api/health")
    def health_check():
        """健康检查接口"""
        return jsonify({
            "status": "ok",
            "message": "灵山胜境AI数字人导游系统运行中",
            "version": "1.0.0"
        })

    # ===== 创建上传目录 =====
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  灵山胜境AI数字人导游系统 v1.0")
    print(f"  Flask服务器启动: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"  WebSocket服务: ws://{FLASK_HOST}:{FLASK_PORT}/ws/chat")
    print(f"  数据库: SQLite (lingshan.db)")
    print(f"{'='*60}\n")

    return app


# ======================== 应用入口 ========================
app = create_app()


if __name__ == "__main__":
    # 启动前初始化数据库
    with app.app_context():
        db.create_all()
        print("[✓] 数据库表已确保创建")

        # 检查是否需要初始化默认数据
        from models import Admin, DigitalHuman
        from config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

        if not Admin.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first():
            admin = Admin(username=DEFAULT_ADMIN_USERNAME)
            admin.set_password(DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            print(f"[✓] 默认管理员已创建：{DEFAULT_ADMIN_USERNAME}/{DEFAULT_ADMIN_PASSWORD}")

        # 初始化默认数字人
        if DigitalHuman.query.count() == 0:
            default_dh = [
                DigitalHuman(name="灵韵（默认导游）", model_path="/live2d_models/lingyun/", is_active=True),
                DigitalHuman(name="慧心（禅意导游）", model_path="/live2d_models/huixin/", default_speed=0.9, default_pitch=1.1, default_voice="zh-CN-XiaoyiNeural", is_active=True),
                DigitalHuman(name="明远（文化导游）", model_path="/live2d_models/mingyuan/", default_speed=1.1, default_pitch=0.9, default_voice="zh-CN-YunxiNeural", is_active=True),
            ]
            for dh in default_dh:
                db.session.add(dh)
            print(f"[✓] 默认数字人已创建")

        db.session.commit()

    # 自动构建知识库
    _auto_build_knowledge_base()

    # 启动Flask服务器
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        threaded=True  # 多线程支持
    )