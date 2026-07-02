"""
==============================================================
RAG知识库检索服务模块
功能：文档切片 -> 向量化 -> ChromaDB存储 -> 相似度检索
==============================================================
"""

import os
import re
import hashlib
from typing import List, Dict, Any

# 导入配置
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import KOWLEDGE_DIR, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, CHROMA_TOP_K

# ======================== 轻量级文本嵌入 ========================
class SimpleEmbedding:
    """
    轻量级文本向量化方案（纯CPU运行，不依赖GPU）
    使用基于词频的哈希向量化方法，无需下载大型模型
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        # 构建常用中文字词特征词典
        self.feature_words = self._build_feature_dict()

    def _build_feature_dict(self) -> List[str]:
        """构建景区相关特征词词典"""
        # 灵山胜境核心词汇
        base_words = [
            "灵山", "大佛", "梵宫", "九龙灌浴", "菩提", "佛教", "禅意",
            "拈花湾", "五印坛城", "曼飞龙塔", "祥符禅寺", "灵山精舍",
            "太湖", "无锡", "景区", "门票", "路线", "游览", "表演",
            "素斋", "住宿", "交通", "导游", "开放时间", "停车场",
            "佛足坛", "阿育王柱", "天下第一掌", "百子戏弥勒", "抱佛脚",
            "文化", "历史", "景点", "参观", "推荐", "攻略", "预约"
        ]
        # 中文常用停用词
        stop_words = set("的了在是有一和我对他不也但这那要于就都会而没吧吗啊呢")
        # 扩展特征词
        expanded = []
        for w in base_words:
            expanded.append(w)
            # 对双字词拆单字作为补充特征
            if len(w) == 2:
                expanded.append(w[0])
                expanded.append(w[1])
        return expanded

    def embed(self, text: str) -> List[float]:
        """
        将文本转换为向量
        使用哈希特征 + TF权重的方法
        """
        if not text or not text.strip():
            return [0.0] * self.dimension

        # 初始化向量
        vector = [0.0] * self.dimension
        total_features = 0

        # 提取文本中的特征词
        for i, word in enumerate(self.feature_words):
            if word in text:
                # 计算词频权重
                count = text.count(word)
                # 使用哈希确定向量位置
                pos = self._hash_to_pos(word, i)
                vector[pos] += count
                total_features += count

        # 对单个字符做补充匹配
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':  # 中文字符范围
                pos = self._hash_to_pos(ch, ord(ch))
                vector[pos] += 0.5

        # L2归一化
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def _hash_to_pos(self, text: str, seed: int = 0) -> int:
        """将文本哈希到向量维度范围内的位置"""
        hash_str = f"{text}_{seed}"
        hash_bytes = hashlib.md5(hash_str.encode("utf-8")).digest()
        pos = int.from_bytes(hash_bytes[:4], "big") % self.dimension
        return pos


# ======================== ChromaDB向量数据库封装 ========================
class VectorDatabase:
    """
    ChromaDB本地向量数据库封装
    提供文档入库、相似度检索功能
    """

    def __init__(self):
        self.embedding = SimpleEmbedding(dimension=384)
        self.collection = None
        self._init_chromadb()

    def _init_chromadb(self):
        """初始化ChromaDB客户端和集合"""
        try:
            import chromadb
            from chromadb.config import Settings

            # 确保持久化目录存在
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

            # 创建chromadb客户端（持久化模式）
            self.client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(anonymized_telemetry=False)
            )

            # 获取或创建集合
            try:
                self.collection = self.client.get_collection(CHROMA_COLLECTION_NAME)
                print(f"[RAG] 加载已有向量库：{CHROMA_COLLECTION_NAME}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=CHROMA_COLLECTION_NAME,
                    metadata={"description": "灵山胜境景区知识库"}
                )
                print(f"[RAG] 创建新向量库：{CHROMA_COLLECTION_NAME}")

        except ImportError:
            print("[RAG] 警告：chromadb未安装，使用内存模式")
            self.client = None
            self.collection = None
        except Exception as e:
            print(f"[RAG] 警告：ChromaDB初始化失败：{e}")
            self.client = None
            self.collection = None

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        将文档列表添加到向量库

        参数：
            documents: 文档字典列表，每项包含 {id, text, metadata}
        """
        if self.collection is None:
            print("[RAG] 向量库未初始化，跳过入库")
            return

        if not documents:
            return

        ids = []
        texts = []
        metadatas = []
        embeddings = []

        for doc in documents:
            doc_id = doc.get("id", str(hash(doc["text"])))
            text = doc["text"]
            metadata = doc.get("metadata", {})

            # 生成向量
            vector = self.embedding.embed(text)

            ids.append(doc_id)
            texts.append(text)
            metadatas.append(metadata)
            embeddings.append(vector)

        # 批量添加（使用自带向量，避免ChromaDB再次嵌入）
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings
        )

        print(f"[RAG] 成功入库 {len(documents)} 条文档")

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        检索与查询最相关的文档

        参数：
            query: 查询文本
            top_k: 返回结果数量

        返回：
            检索结果列表，每项包含 {id, text, metadata, distance}
        """
        if self.collection is None:
            print("[RAG] 向量库未初始化，返回空结果")
            return []

        if top_k is None:
            top_k = CHROMA_TOP_K

        # 生成查询向量
        query_vector = self.embedding.embed(query)

        # 执行检索
        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=min(top_k, 20)
            )

            formatted_results = []
            if results and results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0.0
                    })

            return formatted_results

        except Exception as e:
            print(f"[RAG] 检索失败：{e}")
            return []

    def delete_collection(self):
        """删除当前集合并重新创建"""
        if self.client and self.collection:
            try:
                self.client.delete_collection(CHROMA_COLLECTION_NAME)
                print(f"[RAG] 已删除向量库：{CHROMA_COLLECTION_NAME}")
                # 重新创建集合
                self.collection = self.client.create_collection(
                    name=CHROMA_COLLECTION_NAME,
                    metadata={"description": "灵山胜境景区知识库"}
                )
                print(f"[RAG] 已重新创建向量库：{CHROMA_COLLECTION_NAME}")
            except Exception as e:
                print(f"[RAG] 删除向量库失败：{e}")

    def get_document_count(self) -> int:
        """获取向量库文档总数"""
        if self.collection is None:
            return 0
        try:
            return self.collection.count()
        except Exception:
            return 0


# ======================== 文档切割与知识库构建 ========================
class KnowledgeProcessor:
    """
    知识库文档处理器
    负责读取文档、切片、构建向量库
    """

    def __init__(self):
        self.vector_db = VectorDatabase()

    def extract_text_from_docx(self, file_path: str) -> str:
        """从docx文件提取纯文本（包含表格内容）"""
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = []
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    paragraphs.append(text)
            # 提取表格内容
            table_texts = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells])
                    if row_text.strip():
                        table_texts.append(row_text)
            return "\n".join(paragraphs) + "\n" + "\n".join(table_texts)
        except Exception as e:
            print(f"[RAG] 读取docx失败 {file_path}: {e}")
            return ""

    def extract_text_from_xlsx(self, file_path: str, max_rows: int = 500, target_spots: List[str] = None) -> str:
        """从xlsx文件提取文本数据（限制行数，防止超大文件）
        target_spots: 只提取包含这些关键词的行（用于过滤无关景点数据）
        """
        if target_spots is None:
            target_spots = ["灵山", "灵山胜境", "拈花湾"]
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True)
            texts = []
            total_rows = 0
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                for row in ws.iter_rows(values_only=True):
                    if total_rows >= max_rows:
                        break
                    row_text = " ".join([str(cell) for cell in row if cell is not None])
                    if row_text.strip():
                        # 只保留包含目标景点关键词的行
                        if any(spot in row_text for spot in target_spots):
                            texts.append(row_text)
                    total_rows += 1
                if total_rows >= max_rows:
                    break
            return "\n".join(texts)
        except Exception as e:
            print(f"[RAG] 读取xlsx失败 {file_path}: {e}")
            return ""

    def split_text_to_chunks(self, text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
        """
        将长文本分割成文档块

        参数：
            text: 原始文本
            chunk_size: 每块字符数
            overlap: 块间重叠字符数

        返回：
            文档块列表
        """
        if not text:
            return []

        # 按句子切分
        sentences = re.split(r"([。！？\n])", text)
        chunks = []
        current_chunk = ""

        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")

            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # 重叠处理：保留最后一部分
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + sentence
            else:
                current_chunk += sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    def build_knowledge_base(self, knowledge_dir: str = None) -> int:
        """
        从知识库目录读取所有文档，构建向量库

        参数：
            knowledge_dir: 知识库文档目录路径

        返回：
            入库的文档块数量
        """
        if knowledge_dir is None:
            knowledge_dir = KOWLEDGE_DIR

        if not os.path.exists(knowledge_dir):
            print(f"[RAG] 知识库目录不存在：{knowledge_dir}")
            return 0

        # 扫描目录下的所有文档
        all_text = ""
        file_info = []

        for filename in os.listdir(knowledge_dir):
            file_path = os.path.join(knowledge_dir, filename)
            if not os.path.isfile(file_path):
                continue

            text = ""
            if filename.endswith(".docx"):
                text = self.extract_text_from_docx(file_path)
            elif filename.endswith(".xlsx"):
                text = self.extract_text_from_xlsx(file_path)
            elif filename.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception as e:
                    print(f"[RAG] 读取txt失败 {file_path}: {e}")

            if text:
                all_text += f"\n\n【文档来源：{filename}】\n{text}"
                file_info.append({"filename": filename, "size": len(text)})
                print(f"[RAG] 读取文档：{filename} ({len(text)}字符)")

        if not all_text:
            print("[RAG] 未读取到任何有效文档内容")
            return 0

        # 分割为文档块
        chunks = self.split_text_to_chunks(all_text, chunk_size=200, overlap=50)
        print(f"[RAG] 文档分割完成：共 {len(chunks)} 个文档块")

        # 构建入库数据
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                "id": f"doc_{i}_{hash(chunk) % 1000000}",
                "text": chunk,
                "metadata": {
                    "source": "knowledge_base",
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            })

        # 入库
        self.vector_db.add_documents(documents)

        return len(documents)

    def search_knowledge(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """检索知识库"""
        return self.vector_db.search(query, top_k)

    def get_document_count(self) -> int:
        """获取向量库文档总数"""
        return self.vector_db.get_document_count()

    def get_knowledge_context(self, query: str, top_k: int = None) -> str:
        """
        检索知识库并组装为上下文文本

        参数：
            query: 用户查询
            top_k: 检索数量

        返回：
            拼接后的上下文文本，供LLM使用
        """
        results = self.search_knowledge(query, top_k)
        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(f"[参考{i + 1}] {r['text']}")

        return "\n\n".join(context_parts)


# ======================== 全局单例 ========================
_knowledge_processor = None


def get_knowledge_processor() -> KnowledgeProcessor:
    """获取知识库处理器单例"""
    global _knowledge_processor
    if _knowledge_processor is None:
        _knowledge_processor = KnowledgeProcessor()
    return _knowledge_processor
