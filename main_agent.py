# main_agent.py
import google.generativeai as genai
import os
# LƯU Ý: Import list tools từ file mới (tools_azure.py)
from azure_tools import azure_tools 

# Cấu hình API Key
os.environ["GOOGLE_API_KEY"] = "OOPS" 
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Khởi tạo Gemini Model với bộ Tools mới
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=azure_tools, # <--- Cập nhật biến này
    system_instruction="""
    Bạn là Trợ lý AI quản trị của hệ thống AdventureWorks (E-commerce).
    
    Quy tắc sử dụng công cụ (Tools):
    1. Nếu người dùng hỏi tìm sản phẩm, mô tả sản phẩm, gợi ý sản phẩm (VD: xe đạp leo núi, màu đỏ...):
       -> BẮT BUỘC dùng tool 'search_product_knowledge' (RAG).
       
    2. Nếu người dùng hỏi về số liệu, doanh số, lịch sử bán hàng, số lượng đã bán:
       -> BẮT BUỘC dùng tool 'check_sales_history' (SQL Check).
    
    Lưu ý:
    - Trả lời bằng tiếng Việt tự nhiên.
    - Dựa hoàn toàn vào kết quả tool trả về, không bịa đặt thông tin.
    """
)

# Bắt đầu Chat Session
chat = model.start_chat(enable_automatic_function_calling=True)

def run_chat_interface():
    print("--- ADVENTURE WORKS AI ASSISTANT (CONNECTED AZURE SQL) ---")
    print("Gõ 'exit' để thoát.")
    
    while True:
        user_input = input("\nBạn: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        
        try:
            # Gửi tin nhắn
            response = chat.send_message(user_input)
            print(f"Bot: {response.text}")
        except Exception as e:
            print(f"Lỗi: {e}")

if __name__ == "__main__":
    run_chat_interface()