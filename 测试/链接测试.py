import os
import google.generativeai as genai

def test_gemini_connection():
    try:
        # 从系统环境变量中读取 API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("环境变量 GEMINI_API_KEY 未设置，请确认是否已正确配置。")

        # 配置 Gemini
        genai.configure(api_key=api_key)

        # 选择一个轻量模型进行测试请求
        model = genai.GenerativeModel("gemini-1.5-flash")

        # 发起简单请求，测试连通性
        response = model.generate_content("你好，请回答：1+1等于几？")

        print("✅ 连接成功！Gemini API 返回：", response.text)

    except Exception as e:
        print("❌ 连接失败，错误原因：", str(e))

if __name__ == "__main__":
    test_gemini_connection()
