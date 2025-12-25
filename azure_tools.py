# azure_tools.py
from db_azure_connect import SessionLocal, FactInternetSales, DimProduct, DimProductSubcategory, DimProductCategory
from sqlalchemy import func, or_
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
    
    response_text = "Dữ liệu thô từ hệ thống (Vui lòng dịch và hiển thị theo định dạng thẻ):\n"
    for i, doc in enumerate(results['documents'][0]):
        try:
            meta = results['metadatas'][0][i]
            
            # Lấy đầy đủ thông tin để Gemini có "nguyên liệu"
            name = meta.get('name', 'N/A')
            price = meta.get('price', '0')
            category = meta.get('category', 'N/A')
            subcategory = meta.get('subcategory', 'N/A')
            stock = meta.get('stock', 0)
            reorder = meta.get('reorder_point', 0)
            
            # Đóng gói dữ liệu cực kỳ chi tiết
            response_text += (
                f"--- ITEM_DATA_START ---\n"
                f"Product_Name: {name}\n"
                f"Price: ${price}\n"
                f"Category_Path: {category} > {subcategory}\n"
                f"Stock_Status: {stock} (Reorder at: {reorder})\n"
                f"Original_English_Description: {doc}\n" # Gửi mô tả gốc để AI dịch
                f"--- ITEM_DATA_END ---\n"
            )
        except Exception as e:
            print(f"Lỗi đọc metadata: {e}")
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
def get_top_sellers(search_term: str = None, limit: int = 3):
    """
    Tìm danh sách sản phẩm bán chạy. 
    search_term: Từ khóa tìm kiếm theo loại sản phẩm (ví dụ: 'Road Bikes', 'Mountain Bikes').
    limit: Số lượng sản phẩm muốn hiển thị.
    """
    session = SessionLocal()
    try:
        # Khởi tạo Query cơ bản
        query = session.query(
            DimProduct.EnglishProductName,
            func.sum(FactInternetSales.OrderQuantity).label('TotalSold')
        ).join(FactInternetSales, FactInternetSales.ProductKey == DimProduct.ProductKey)\
         .join(DimProductSubcategory, DimProduct.ProductSubcategoryKey == DimProductSubcategory.ProductSubcategoryKey)\
         .join(DimProductCategory, DimProductSubcategory.ProductCategoryKey == DimProductCategory.ProductCategoryKey)

        # Nếu có search_term (do Gemini truyền vào), thực hiện lọc
        if search_term:
            query = query.filter(
                or_(
                    DimProductCategory.EnglishProductCategoryName.like(f"%{search_term}%"),
                    DimProductSubcategory.EnglishProductSubcategoryName.like(f"%{search_term}%")
                )
            )

        top_results = query.group_by(DimProduct.EnglishProductName)\
                           .order_by(func.sum(FactInternetSales.OrderQuantity).desc())\
                           .limit(limit).all()

        if not top_results:
            return f"Không tìm thấy dữ liệu bán chạy cho từ khóa: '{search_term}'"

        result_text = f"🏆 TOP {len(top_results)} SẢN PHẨM BÁN CHẠY NHẤT ({search_term if search_term else 'Tất cả'}):\n"
        for name, total in top_results:
            result_text += f"- **{name}**: Đã bán {int(total)} chiếc 📈\n"
        
        return result_text

    except Exception as e:
        return f"Lỗi truy vấn SQL: {str(e)}"
    finally:
        session.close()

# Danh sách tools
azure_tools = [search_product_knowledge, check_sales_history, order_product, get_top_sellers]