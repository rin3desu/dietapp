import os
import google.generativeai as genai

# 環境変数を直接ここでセット（テストのため）
# さきほど取得したAPIキーをここに貼り付けてみてください
os.environ["GEMINI_API_KEY"] = "AIzaSyBkts6kKpSs-t9mReLgdGB9XietIhSjsBA"

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

try:
    print("利用可能なモデル一覧:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"エラーが発生しました: {e}")