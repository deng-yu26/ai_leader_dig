#!/usr/bin/env python3
"""
==============================================================
【灵山胜境AI数字人导游系统】一键启动脚本
功能：初始化数据库、向量库、创建默认管理员，启动Flask服务器
==============================================================
"""

import os
import sys
import subprocess
import time

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

print("""
╔══════════════════════════════════════════════════════════╗
║       灵山胜境AI数字人导游系统 v1.0                       ║
║       Lingshan AI Digital Human Guide System             ║
╚══════════════════════════════════════════════════════════╝
""")


def check_python_dependencies():
    """检查并安装Python依赖"""
    print("\n[1/4] 正在检查Python依赖...")
    requirements_file = os.path.join(BACKEND_DIR, "requirements.txt")

    if not os.path.exists(requirements_file):
        print(f"[!] 找不到 requirements.txt: {requirements_file}")
        return False

    try:
        # 使用pip安装依赖
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )

        if result.returncode == 0:
            print("[✓] 依赖安装完成")
        else:
            print(f"[!] 部分依赖安装可能存在问题：{result.stderr[-500:]}")
        return True

    except Exception as e:
        print(f"[!] 依赖检查失败：{e}")
        return False


def init_database():
    """初始化数据库"""
    print("\n[2/4] 正在初始化数据库...")
    init_script = os.path.join(BACKEND_DIR, "init_db.py")

    if not os.path.exists(init_script):
        print(f"[!] 找不到初始化脚本: {init_script}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, init_script],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )
        print(result.stdout)
        if result.stderr:
            print(f"[!] 警告：{result.stderr[-500:]}")
        return True

    except Exception as e:
        print(f"[!] 数据库初始化失败：{e}")
        return False


def init_vector_db():
    """初始化向量库（从知识库文档构建）"""
    print("\n[3/4] 正在初始化向量库（从知识库文档构建）...")
    try:
        # 直接调用RAG服务进行初始化
        sys.path.insert(0, BACKEND_DIR)
        from services.rag_service import get_knowledge_processor

        processor = get_knowledge_processor()
        count = processor.build_knowledge_base()

        if count > 0:
            print(f"[✓] 向量库构建完成，共入库 {count} 条文档")
        else:
            print("[i] 知识库文档为空或未找到，请将文档放入 knowledge/ 目录")
        return True

    except Exception as e:
        print(f"[!] 向量库初始化失败：{e}")
        print("[i] 可在启动后通过管理后台手动同步知识库")
        return False


def start_server():
    """启动Flask服务器"""
    print("\n[4/4] 正在启动Flask服务器...\n")
    app_script = os.path.join(BACKEND_DIR, "app.py")

    try:
        # 启动Flask应用
        subprocess.run([sys.executable, app_script], cwd=BACKEND_DIR)
    except KeyboardInterrupt:
        print("\n[i] 服务器已停止")
    except Exception as e:
        print(f"[!] 服务器启动失败：{e}")
        sys.exit(1)


def main():
    """主流程"""
    print("正在启动系统，请稍候...\n")

    # 步骤1：检查依赖
    check_python_dependencies()

    # 步骤2：初始化数据库
    init_database()

    # 步骤3：初始化向量库
    init_vector_db()

    # 步骤4：启动服务器
    start_server()


if __name__ == "__main__":
    main()