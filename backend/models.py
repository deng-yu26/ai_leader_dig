"""
==============================================================
数据库模型定义 —— 五张核心数据表
使用 Flask-SQLAlchemy ORM 管理
密码存储强制使用 Werkzeug 哈希加密
==============================================================
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ======================== 1. 管理员表 ========================
class Admin(db.Model):
    """管理员账号表"""
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, comment="管理员账号")
    password_hash = db.Column(db.String(256), nullable=False, comment="密码哈希值")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def set_password(self, password: str):
        """使用 Werkzeug 加密存储密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """校验密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    def __repr__(self):
        return f"<Admin {self.username}>"


# ======================== 2. 游客用户表 ========================
class User(db.Model):
    """游客用户表"""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, comment="用户名")
    password_hash = db.Column(db.String(256), nullable=False, comment="登录密码哈希")
    phone = db.Column(db.String(20), nullable=True, comment="手机号")
    email = db.Column(db.String(128), nullable=True, comment="邮箱")
    registered_at = db.Column(db.DateTime, default=datetime.now, comment="注册时间")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "email": self.email,
            "registered_at": self.registered_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    def __repr__(self):
        return f"<User {self.username}>"


# ======================== 3. 对话日志表 ========================
class ChatLog(db.Model):
    """对话日志表 —— 记录每一次用户与AI数字人的完整问答"""
    __tablename__ = "chat_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False, comment="用户唯一标识")
    question_text = db.Column(db.Text, nullable=False, comment="用户提问文本")
    answer_text = db.Column(db.Text, nullable=False, comment="AI完整回答文本")
    question_time = db.Column(db.DateTime, default=datetime.now, comment="提问时间")
    emotion_label = db.Column(db.String(32), default="平静", comment="AI回复情绪标签（平静/微笑/热情）")
    voice_duration = db.Column(db.Float, default=0.0, comment="语音播放时长（秒）")
    digital_human_id = db.Column(db.Integer, default=1, comment="使用数字人形象ID")
    tts_voice = db.Column(db.String(64), default="zh-CN-XiaoxiaoNeural", comment="使用TTS音色ID")
    image_path = db.Column(db.String(256), nullable=True, comment="用户上传的图片路径（可选）")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "question_time": self.question_time.strftime("%Y-%m-%d %H:%M:%S"),
            "emotion_label": self.emotion_label,
            "voice_duration": self.voice_duration,
            "digital_human_id": self.digital_human_id,
            "tts_voice": self.tts_voice,
            "image_path": self.image_path
        }

    def __repr__(self):
        return f"<ChatLog {self.id} by user {self.user_id}>"


# ======================== 4. FAQ知识库表 ========================
class FaqKnowledge(db.Model):
    """FAQ知识库表 —— 存储景区常见问答对"""
    __tablename__ = "faq_knowledge"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.Text, nullable=False, comment="问题")
    answer = db.Column(db.Text, nullable=False, comment="对应答案")
    doc_source = db.Column(db.String(256), nullable=True, comment="文档来源")
    vector_sync = db.Column(db.Boolean, default=False, comment="向量库同步状态（True=已同步）")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "doc_source": self.doc_source,
            "vector_sync": self.vector_sync,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    def __repr__(self):
        return f"<FaqKnowledge {self.id}: {self.question[:30]}>"


# ======================== 5. 数字人配置表 ========================
class DigitalHuman(db.Model):
    """数字人配置表 —— 管理Live2D数字人形象与参数"""
    __tablename__ = "digital_human"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False, comment="数字人名称")
    model_path = db.Column(db.String(256), nullable=False, comment="Live2D模型文件存储路径（相对路径）")
    default_speed = db.Column(db.Float, default=1.0, comment="默认语速（0.5-2.0）")
    default_pitch = db.Column(db.Float, default=1.0, comment="默认语调（0.5-2.0）")
    default_voice = db.Column(db.String(64), default="zh-CN-XiaoxiaoNeural", comment="默认音色")
    is_active = db.Column(db.Boolean, default=True, comment="启用状态")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "model_path": self.model_path,
            "default_speed": self.default_speed,
            "default_pitch": self.default_pitch,
            "default_voice": self.default_voice,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    def __repr__(self):
        return f"<DigitalHuman {self.name}>"
