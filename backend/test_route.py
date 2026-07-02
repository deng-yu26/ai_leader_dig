"""测试路线推荐问题"""
import sys
sys.path.insert(0, ".")
from services.rag_service import get_knowledge_processor
from services.llm_service import get_llm_service

rag = get_knowledge_processor()
llm = get_llm_service()

system_prompt = """你是一个专业的灵山胜境景区AI导游。你的职责是回答关于灵山胜境景区（含拈花湾禅意小镇）的所有问题。

## 回答规则（严格遵守）：
1. 你只能回答与灵山胜境景区、拈花湾禅意小镇相关的内容。
2. 如果用户问的问题与景区无关，请友好地引导用户询问景区相关问题。
3. 回答内容要热情、生动、有感染力，适合导游讲解风格。
4. 基于提供的知识库上下文进行回答，不要编造事实。
5. 如果知识库中没有相关信息，请如实告知用户，并提供其他相关景点的介绍。
6. 推荐游览路线时，可以结合用户的兴趣点和时间安排给出个性化建议。"""

q = "有什么推荐的游览路线？"
context = rag.get_knowledge_context(q, top_k=5)

print(f"RAG检索上下文 ({len(context)} 字符)\n")
print(context[:600] + ("..." if len(context) > 600 else ""))

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"知识库参考信息：\n{context}\n\n用户问题：{q}"}
]

answer = llm.chat(messages)
print(f"\n\nAI回答：\n")
print(answer)