import requests

# 专门负责与你的 RTX 4060 沟通的 AI 引擎
class AIEngine:
    def __init__(self, model="deepseek-r1:7b"):
        self.url = "http://localhost:11434/api/generate"
        self.model = model
        # 强制植入你的专业背景和 180cm 视角
        self.system_prompt = "你是一个硬核数据科学导师。禁止使用AI套话。使用极客风格。视角：180cm大学生。"

    def generate(self, prompt, timeout=300):
        full_prompt = f"{self.system_prompt}\n\n任务：{prompt}"
        payload = {"model": self.model, "prompt": full_prompt, "stream": False}
        try:
            response = requests.post(self.url, json=payload, timeout=timeout)
            return response.json().get('response', "思考超时...")
        except Exception as e:
            return f"❌ 引擎连接失败: {str(e)}"
