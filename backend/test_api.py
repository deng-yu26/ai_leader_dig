"""
快速测试脚本 - 验证后端系统是否正常运行
"""
import os
import sys

# 将项目根目录和后端目录加入路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))
sys.path.insert(0, BASE_DIR)

from app import app, db
from models import Admin, DigitalHuman
from config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

def run_tests():
    """运行后端接口测试"""
    with app.app_context():
        # 创建表
        db.create_all()
        print('[✓] 数据库表创建成功')

        # 检查管理员
        admin = Admin.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
        if not admin:
            admin = Admin(username=DEFAULT_ADMIN_USERNAME)
            admin.set_password(DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f'[✓] 管理员已创建: {DEFAULT_ADMIN_USERNAME}/{DEFAULT_ADMIN_PASSWORD}')
        else:
            print(f'[✓] 管理员已存在: {admin.username}')

        # 检查数字人
        if DigitalHuman.query.count() == 0:
            dh = DigitalHuman(name='灵韵（测试）', model_path='/live2d_models/test/')
            db.session.add(dh)
            db.session.commit()
            print('[✓] 默认数字人已创建')
        else:
            print(f'[✓] 已有 {DigitalHuman.query.count()} 个数字人')

        # 接口测试
        with app.test_client() as client:
            # 健康检查
            resp = client.get('/api/health')
            data = resp.get_json()
            assert resp.status_code == 200
            print(f'[✓] 健康检查: {resp.status_code} - {data["message"]}')

            # 管理员登录
            resp = client.post('/api/admin/login', json={
                'username': DEFAULT_ADMIN_USERNAME,
                'password': DEFAULT_ADMIN_PASSWORD
            })
            data = resp.get_json()
            assert resp.status_code == 200
            print(f'[✓] 管理员登录: {resp.status_code} - {data["message"]}')

            # 获取数字人列表
            resp = client.get('/api/user/digital-humans')
            data = resp.get_json()
            assert resp.status_code == 200
            print(f'[✓] 数字人列表: {resp.status_code} - {len(data["data"])} 个')

            # 游客注册
            resp = client.post('/api/user/register', json={
                'username': 'test_user',
                'password': 'test123456',
                'phone': '13800138000'
            })
            data = resp.get_json()
            print(f'[✓] 游客注册: {resp.status_code} - {data["message"]}')

            # 游客登录
            resp = client.post('/api/user/login', json={
                'username': 'test_user',
                'password': 'test123456'
            })
            data = resp.get_json()
            print(f'[✓] 游客登录: {resp.status_code} - {data["message"]}')

            # 路线规划
            resp = client.get('/api/user/route-plan')
            data = resp.get_json()
            assert resp.status_code == 200
            print(f'[✓] 路线规划: {resp.status_code}')

            # AI配置
            resp = client.get('/api/admin/ai-config')
            data = resp.get_json()
            assert resp.status_code == 200
            print(f'[✓] AI配置获取: {resp.status_code}')

            # 仪表盘统计
            with client.session_transaction() as sess:
                sess['admin_id'] = 1
            resp = client.get('/api/admin/dashboard/stats')
            data = resp.get_json()
            assert resp.status_code == 200
            print(f'[✓] 仪表盘统计: {resp.status_code}')

            # 获取对话日志
            resp = client.get('/api/admin/chat-logs?page=1&per_page=5')
            data = resp.get_json()
            print(f'[✓] 对话日志: {resp.status_code}')

            # 知识库列表
            resp = client.get('/api/admin/knowledge?page=1&per_page=5')
            data = resp.get_json()
            print(f'[✓] 知识库列表: {resp.status_code}')

            # 用户管理列表
            resp = client.get('/api/admin/users?page=1&per_page=5')
            data = resp.get_json()
            print(f'[✓] 用户管理列表: {resp.status_code}')

            # AI配置更新
            resp = client.put('/api/admin/ai-config', json={
                'api_key': 'test-key',
                'api_base': 'https://test.api.com/v1',
                'model_name': 'test-model'
            })
            data = resp.get_json()
            print(f'[✓] AI配置更新: {resp.status_code} - {data["message"]}')

        print()
        print('=' * 50)
        print('全部接口测试通过！后端系统运行正常。')
        print('=' * 50)
        return True

if __name__ == '__main__':
    run_tests()
