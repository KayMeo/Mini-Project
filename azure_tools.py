# azure_tools.py
from db_azure_connect import SessionLocal, FactInternetSales, DimProduct
from sqlalchemy import func
import chromadb

# Đường dẫn thư mục lưu trữ (Phải khớp với file ingestion)
PERSIST_DIRECTORY = "./chroma_db" 

# --- SỬA LỖI TẠI ĐÂY: Dùng PersistentClient thay vì Client ---
try:
    # Cố gắng dùng PersistentClient (cho bản ChromaDB mới)
    chroma_client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
except AttributeError:
    # Dự phòng nếu máy bạn dùng bản cũ (ít khả năng xảy ra nếu bạn vừa update)
    chroma_client = chromadb.Client(path=PERSIST_DIRECTORY)

# Lấy collection đã tạo
collection = chroma_client.get_collection(name="adventureworks_products")

# --- Tool 1: RAG Search ---
def search_product_knowledge(query: str):
    """Tìm thông tin sản phẩm (mô tả, đặc điểm) bằng ngôn ngữ tự nhiên."""
    print(f"\n[RAG] Đang tìm kiếm vector cho: '{query}'")
    
    # Query vector
    results = collection.query(
        query_texts=[query], 
        n_results=3
    )
    
    if not results['documents'] or not results['documents'][0]:
        return "Không tìm thấy sản phẩm phù hợp trong tài liệu."
    
    response_text = "Dựa trên dữ liệu mô tả, tôi tìm thấy:\n"
    for i, doc in enumerate(results['documents'][0]):
        try:
            meta = results['metadatas'][0][i]
            
            # Lấy thêm Subcategory
            name = meta.get('name', 'Sản phẩm')
            price = meta.get('price', 'N/A')
            category = meta.get('category', 'N/A')
            subcategory = meta.get('subcategory', 'N/A') # <--- LẤY SUB-CATEGORY MỚI
            
            response_text += (
                f"- **{name}** (${price})\n"
                f"  - Phân loại: {category} > {subcategory}\n" # <--- HIỂN THỊ CẢ HAI
                f"  - Mô tả RAG: {doc}\n"
            )
        except:
            continue
        
    return response_text

# --- Tool 2: SQL Check ---
def check_sales_history(product_name: str):
    """Kiểm tra lịch sử bán hàng từ SQL."""
    session = SessionLocal()
    print(f"\n[SQL] Đang tra cứu doanh số cho: {product_name}")
    
    product = session.query(DimProduct).filter(DimProduct.EnglishProductName.ilike(f"%{product_name}%")).first()
    
    if not product:
        session.close()
        return "Không tìm thấy tên sản phẩm này trong database SQL."
    
    total_sales = session.query(func.sum(FactInternetSales.OrderQuantity))\
        .filter(FactInternetSales.ProductKey == product.ProductKey).scalar()
        
    session.close()
    return f"Sản phẩm '{product.EnglishProductName}' đã bán được tổng cộng {total_sales or 0} chiếc."

# --- Tool 3: Đặt hàng & Auto Restock ---
def order_product(product_name: str, quantity: int, user_id: str = "demo_user"):
    """
    Đặt hàng và tự động nhập kho (Restock) nếu chạm ngưỡng ReorderPoint.
    """
    if quantity <= 0:
        return "Số lượng phải lớn hơn 0."
        
    print(f"\n[MCP] Xử lý đơn hàng: '{product_name}' (SL: {quantity})")

    # 1. Tìm sản phẩm
    search_results = collection.query(query_texts=[product_name], n_results=1)
    if not search_results['metadatas'] or not search_results['metadatas'][0]:
        return f"Không tìm thấy sản phẩm '{product_name}'."
        
    meta = search_results['metadatas'][0][0]
    product_id = search_results['ids'][0]
    
    # Lấy thông tin kho từ Metadata
    current_stock = int(meta.get('stock', 0))
    reorder_point = int(meta.get('reorder_point', 10))
    safety_stock = int(meta.get('safety_stock', 100))
    
    # 2. Kiểm tra đủ hàng không
    if current_stock < quantity:
        return f"Kho chỉ còn {current_stock} sản phẩm. Không đủ giao (Cần tối thiểu {quantity})."

    # 3. Trừ kho
    new_stock = current_stock - quantity
    restock_msg = ""
    
    # --- LOGIC TỰ ĐỘNG RESTOCK ---
    if new_stock <= reorder_point:
        print(f"⚠️ CẢNH BÁO: Tồn kho ({new_stock}) chạm ngưỡng Reorder ({reorder_point}).")
        print(f"🔄 Đang tự động nhập kho lên mức an toàn ({safety_stock})...")
        
        # Tự động đẩy tồn kho lên lại mức SafetyStock
        new_stock = safety_stock 
        
        restock_msg = (
            f"\n\n⚠️ **CẢNH BÁO HỆ THỐNG:**\n"
            f"Sau đơn hàng này, tồn kho đã chạm mức báo động (Reorder Point: {reorder_point}).\n"
            f"🔄 **Hệ thống đã TỰ ĐỘNG NHẬP KHO (Auto-Restock)** lên mức an toàn: {safety_stock} sản phẩm."
        )
    # -----------------------------

    # 4. Cập nhật Metadata mới
    meta['stock'] = new_stock
    collection.update(ids=[product_id], metadatas=[meta])

    # 5. Phản hồi
    return (
        f"✅ **ĐẶT HÀNG THÀNH CÔNG!**\n"
        f"- Sản phẩm: {product_name}\n"
        f"- Số lượng đặt: {quantity}\n"
        f"- Tồn kho hiện tại: {new_stock} (Đã cập nhật).{restock_msg}"
    )

# --- Tool 4: Lấy danh sách sản phẩm bán chạy nhất ---
def get_top_sellers(limit: int = 5):
    """
    Truy vấn Azure SQL để lấy N sản phẩm có số lượng bán (OrderQuantity) cao nhất.
    """
    session = SessionLocal()
    print(f"\n[SQL] Đang truy vấn TOP {limit} sản phẩm bán chạy nhất...")
    
    # Truy vấn SQL (Dùng JOIN và GROUP BY)
    top_products = session.query(
        DimProduct.EnglishProductName,
        func.sum(FactInternetSales.OrderQuantity).label('TotalSold')
    ).join(FactInternetSales, FactInternetSales.ProductKey == DimProduct.ProductKey)\
     .group_by(DimProduct.EnglishProductName)\
     .order_by(func.sum(FactInternetSales.OrderQuantity).desc())\
     .limit(limit)\
     .all()
     
    session.close()
    
    if not top_products:
        return "Không có dữ liệu bán hàng trong database."
        
    response_list = []
    for name, total_sold in top_products:
        response_list.append(f"- **{name}**: {total_sold} chiếc")
        
    return f"🏆 Dưới đây là TOP {len(top_products)} sản phẩm bán chạy nhất:\n" + "\n".join(response_list)

# Danh sách tools
azure_tools = [search_product_knowledge, check_sales_history, order_product, get_top_sellers]