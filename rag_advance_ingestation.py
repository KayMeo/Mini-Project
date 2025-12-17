# rag_advanced_ingestion.py
import chromadb
import random
from sqlalchemy.orm import joinedload
from db_azure_connect import SessionLocal, DimProduct, DimProductSubcategory, DimProductCategory

# Đường dẫn để lưu trữ Vector Database
PERSIST_DIRECTORY = "./chroma_db" 

# --- SỬA ĐỔI QUAN TRỌNG: Dùng PersistentClient ---
print(f"--- Khởi tạo Vector Database tại: {PERSIST_DIRECTORY} ---")
chroma_client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

# Xóa collection cũ (nếu có) để nạp lại từ đầu
try:
    chroma_client.delete_collection("adventureworks_products")
    print("--- Đã xóa Collection cũ ---")
except:
    pass

# Tạo collection mới
collection = chroma_client.create_collection(name="adventureworks_products")
print(f"--- Đã tạo Collection mới ---")

def fetch_and_vectorize_products():
    session = SessionLocal()
    print("--- Đang lấy dữ liệu từ Azure SQL... ---")
    
    # Lấy 500 sản phẩm
    products = session.query(DimProduct)\
        .join(DimProductSubcategory)\
        .join(DimProductCategory)\
        .filter(DimProduct.EnglishDescription != None)\
        .limit(500).all()

    documents = []
    ids = []
    metadatas = []

    print(f"--- Đang xử lý {len(products)} sản phẩm... ---")

    for p in products:
        # Xử lý các trường cơ bản
        cat_name = p.subcategory.category.EnglishProductCategoryName or "Uncategorized"
        sub_name = p.subcategory.EnglishProductSubcategoryName or "General"
        price = p.ListPrice if p.ListPrice is not None else 0.0
        desc = p.EnglishDescription if p.EnglishDescription is not None else ""
        
        # --- LOGIC TỒN KHO THÔNG MINH ---
        # Lấy giá trị từ DB, nếu null thì gán mặc định
        safe_stock = p.SafetyStockLevel if p.SafetyStockLevel else 100
        reorder_point = p.ReorderPoint if p.ReorderPoint else 10
        
        # Đảm bảo logic: Safe > Reorder (đề phòng dữ liệu lỗi)
        if safe_stock <= reorder_point:
            safe_stock = reorder_point + 50

        # Random tồn kho hiện tại nằm giữa ngưỡng Min và Max
        current_stock = random.randint(reorder_point, safe_stock)
        # --------------------------------

        contextual_text = (
            f"Sản phẩm: {p.EnglishProductName}. "
            f"Phân loại: {cat_name} > {sub_name}. "
            f"Giá: ${price}. "
            f"Mô tả: {desc}"
        )

        documents.append(contextual_text)
        ids.append(str(p.ProductKey))
        
        # Lưu ngưỡng vào Metadata để Tool dùng
        metadatas.append({
            "product_key": p.ProductKey,
            "name": p.EnglishProductName,
            "price": price,
            "category": cat_name,
            "subcategory": sub_name,
            "stock": current_stock,
            "reorder_point": reorder_point,   # Lưu điểm kích hoạt restock
            "safety_stock": safe_stock        # Lưu mức cần restock lên
        })

    print("--- Đang Vectorize (Local CPU)... ---")
    
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        end = min(i + batch_size, len(documents))
        print(f"   -> Đang nạp batch {i} đến {end}...")
        collection.add(
            documents=documents[i:end],
            ids=ids[i:end],
            metadatas=metadatas[i:end]
        )
    
    print("--- ✅ Hoàn tất nạp dữ liệu! (Dữ liệu đã tự động được lưu) ---")
    session.close()

if __name__ == "__main__":
    fetch_and_vectorize_products()