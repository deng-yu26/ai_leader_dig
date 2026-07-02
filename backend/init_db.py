"""
==============================================================
数据库初始化脚本
功能：创建所有数据表、初始化默认管理员账号、初始化默认数字人形象
==============================================================
"""

import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Admin, DigitalHuman
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD
)


def create_app():
    """创建一个临时的Flask应用用于数据库初始化"""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    db.init_app(app)
    return app


def init_database():
    """初始化数据库：建表 + 默认数据"""
    app = create_app()

    with app.app_context():
        # 创建所有数据表
        db.create_all()
        print("[✓] 数据库表创建完成")

        # ===== 检查并创建默认管理员账号 =====
        admin = Admin.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
        if not admin:
            admin = Admin(username=DEFAULT_ADMIN_USERNAME)
            admin.set_password(DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f"[✓] 默认管理员账号创建完成：{DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
        else:
            print(f"[i] 管理员账号已存在，跳过创建")

        # ===== 检查并创建默认数字人形象 =====
        default_humans = [
            {
                "name": "灵韵（默认导游）",
                "model_path": "/live2d_models/lingyun/",
                "default_speed": 1.0,
                "default_pitch": 1.0,
                "default_voice": "zh-CN-XiaoxiaoNeural",
                "is_active": True
            },
            {
                "name": "慧心（禅意导游）",
                "model_path": "/live2d_models/huixin/",
                "default_speed": 0.9,
                "default_pitch": 1.1,
                "default_voice": "zh-CN-XiaoyiNeural",
                "is_active": True
            },
            {
                "name": "明远（文化导游）",
                "model_path": "/live2d_models/mingyuan/",
                "default_speed": 1.1,
                "default_pitch": 0.9,
                "default_voice": "zh-CN-YunxiNeural",
                "is_active": True
            }
        ]

        for dh_data in default_humans:
            existing = DigitalHuman.query.filter_by(name=dh_data["name"]).first()
            if not existing:
                dh = DigitalHuman(**dh_data)
                db.session.add(dh)
                print(f"[✓] 默认数字人创建完成：{dh_data['name']}")
            else:
                print(f"[i] 数字人 {dh_data['name']} 已存在，跳过创建")

        db.session.commit()
        print("\n[✓] 数据库初始化全部完成！")
        print(f"[i] 数据库文件位置：{SQLALCHEMY_DATABASE_URI}")


if __name__ == "__main__":
    init_database()
