import streamlit as st
import google.generativeai as genai
import os
import time

# Import bộ tools đã xây dựng
# Đảm bảo bạn đã có file azure_tools.py và db_azure_connect.py cùng thư mục
from azure_tools import azure_tools

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="AdventureWorks Assistant",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CẤU HÌNH API & MODEL ---
# ⚠️ THAY API KEY CỦA BẠN VÀO ĐÂY
os.environ["GOOGLE_API_KEY"] = "AIzaSyDpxIeFmi8lpNmLY71kKM_Bu5XlP9I4SzY" 
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# System Instruction: "Bộ não" chỉ đạo cách hiển thị
SYSTEM_INSTRUCTION = """
Bạn là Trợ lý AI quản trị chuyên nghiệp của AdventureWorks.

QUY TẮC HIỂN THỊ (QUAN TRỌNG):
1. **Dùng Emoji làm hình ảnh:**
   - 🚲 (Xe đạp), 👕 (Quần áo), ⛑️ (Phụ kiện), ⚙️ (Linh kiện), 📦 (Khác).
   
2. **Định dạng thẻ sản phẩm (Markdown):**
   Khi tìm thấy sản phẩm, hãy hiển thị theo mẫu sau:
   ### [Emoji] **[Tên Sản Phẩm]**
   - 🏷️ **Phân loại:** [Category] > [Subcategory]
   - 💵 **Giá:** $[Giá]
   - 📦 **Kho:** [Nếu stock <= reorder: 🔴 CẢNH BÁO (Stock/Reorder) | ✅ Sẵn hàng (Stock)]
   - 📝 **Mô tả:** *[Mô tả ngắn gọn]*
   ---

3. **Bảng so sánh:** Nếu có >2 sản phẩm, hãy kẻ bảng Markdown.
4. **SQL & Số liệu:** Khi trả lời về doanh số, hãy in đậm con số và dùng emoji 📈.
5. **Đặt hàng/Restock:** Nếu có sự kiện Auto-Restock, hãy dùng ⚠️ và in đậm để cảnh báo.
"""

# Khởi tạo Session State (Lưu lịch sử chat)
if "history" not in st.session_state:
    st.session_state.history = []

if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash', # Dùng model mới nhất
            tools=azure_tools,
            system_instruction=SYSTEM_INSTRUCTION
        )
        st.session_state.chat_session = model.start_chat(enable_automatic_function_calling=True)
    except Exception as e:
        st.error(f"Lỗi khởi tạo Model: {e}")

# --- 3. GIAO DIỆN SIDEBAR (Bảng điều khiển) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Microsoft_SQL_Server_Logo.svg/1200px-Microsoft_SQL_Server_Logo.svg.png", width=50)
    st.title("Admin Dashboard")
    st.markdown("---")
    
    st.subheader("🛠️ Trạng thái hệ thống")
    st.success("🟢 Azure SQL Database: Connected")
    st.success("🟢 ChromaDB (RAG): Ready")
    st.info("🤖 Model: Gemini 2.5 Flash")
    
    st.markdown("---")
    st.subheader("⚡ Demo Nhanh (Click để chạy)")
    
    # Các nút bấm nhanh kịch bản Demo
    if st.button("🔍 Tìm xe đạp Road màu đỏ"):
        st.session_state.prompt_trigger = "Tìm cho tôi các loại xe đạp Road màu đỏ, hiển thị chi tiết tồn kho."
    
    if st.button("📊 Check doanh số Road-150"):
        st.session_state.prompt_trigger = "Kiểm tra doanh số bán hàng tổng cộng của sản phẩm Road-150 Red."
        
    if st.button("📦 Check kho & Reorder Point"):
        st.session_state.prompt_trigger = "Kiểm tra tồn kho hiện tại và ngưỡng Reorder Point của Mountain-200 Black."
        
    if st.button("🛒 Đặt hàng (Test Restock)"):
        st.session_state.prompt_trigger = "Tôi muốn đặt mua 20 chiếc Mountain-200 Black. Xử lý đơn hàng ngay."

    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử Chat"):
        st.session_state.history = []
        st.session_state.chat_session.history = []
        st.rerun()

# --- 4. GIAO DIỆN CHÍNH (MAIN CHAT) ---
st.title("🚲 AdventureWorks Smart Assistant")
st.caption("Hệ thống trợ lý ảo tích hợp RAG & Azure SQL cho quản trị kho hàng")

# Container chứa nội dung chat
chat_container = st.container()

# Hiển thị lịch sử chat
with chat_container:
    for message in st.session_state.history:
        with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🤖"):
            st.markdown(message["content"])

# --- 5. XỬ LÝ INPUT (Từ thanh chat hoặc nút bấm Sidebar) ---
user_input = st.chat_input("Nhập câu hỏi của bạn tại đây...")

# Kiểm tra xem có lệnh từ nút bấm Sidebar không
if "prompt_trigger" in st.session_state and st.session_state.prompt_trigger:
    user_input = st.session_state.prompt_trigger
    del st.session_state.prompt_trigger # Xóa lệnh sau khi lấy

# Logic xử lý chính
if user_input:
    # 1. Hiển thị tin nhắn người dùng
    with chat_container:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
    st.session_state.history.append({"role": "user", "content": user_input})

    # 2. Gọi Gemini xử lý
    with chat_container:
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            message_placeholder.markdown("⏳ *Đang tra cứu dữ liệu từ Azure SQL & Vector DB...*")
            
            try:
                # Gửi tin nhắn
                response = st.session_state.chat_session.send_message(user_input)
                full_response = response.text
                
                # Hiệu ứng gõ chữ (Typewriter effect) cho mượt
                displayed_response = ""
                for chunk in full_response.split(): 
                    displayed_response += chunk + " "
                    time.sleep(0.02) # Tốc độ gõ
                    message_placeholder.markdown(displayed_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                # Lưu lịch sử
                st.session_state.history.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                message_placeholder.error(f"❌ Lỗi hệ thống: {str(e)}")