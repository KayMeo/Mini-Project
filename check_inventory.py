# check_random.py
import chromadb
import random

# Đường dẫn thư mục lưu trữ
PERSIST_DIRECTORY = "./chroma_db"

print(f"--- Đang kết nối và lấy mẫu ngẫu nhiên từ: {PERSIST_DIRECTORY} ---")

try:
    # 1. Kết nối
    client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
    collection = client.get_collection(name="adventureworks_products")
    
    # 2. Lấy danh sách tất cả ID
    all_data = collection.get(include=[]) 
    all_ids = all_data['ids']
    total_count = len(all_ids)
    
    print(f"✅ Tổng số sản phẩm trong kho: {total_count}")

    if total_count == 0:
        print("⚠️ Database rỗng! Hãy chạy file rag_advanced_ingestion.py trước.")
    else:
        # 3. Chọn ngẫu nhiên 5 ID
        sample_size = min(5, total_count)
        random_ids = random.sample(all_ids, sample_size)
        
        # 4. Lấy chi tiết của 5 ID này
        results = collection.get(ids=random_ids)
        
        print(f"\n--- 🎲 5 SẢN PHẨM NGẪU NHIÊN ĐỂ TEST ---")
        
        for i in range(len(results['ids'])):
            meta = results['metadatas'][i]
            
            # Lấy thông tin cơ bản
            name = meta.get('name', 'N/A')
            price = meta.get('price', 'N/A')
            cat = meta.get('category', 'N/A')
            sub = meta.get('subcategory', 'N/A')
            
            # Lấy thông tin KHO HÀNG (Quan trọng)
            stock = int(meta.get('stock', 0))
            reorder = int(meta.get('reorder_point', 0))
            safety = int(meta.get('safety_stock', 0))
            
            # Tính toán số lượng cần mua để KÍCH HOẠT RESTOCK
            # Công thức: Mua sao cho (Stock - Mua) <= Reorder
            # => Mua ít nhất = Stock - Reorder
            buy_to_trigger = stock - reorder
            
            print(f"\n📦 SẢN PHẨM #{i+1}: {name}")
            print(f"   ► Phân loại: {cat} > {sub}")
            print(f"   ► Giá: ${price}")
            print(f"   ► TỒN KHO HIỆN TẠI: {stock}")
            print(f"   ► Ngưỡng báo động (Reorder Point): {reorder}")
            print(f"   ► Mức hồi phục (Safety Stock): {safety}")
            
            print(f"   🎯 GỢI Ý KỊCH BẢN DEMO:")
            print(f"     1. Hỏi tồn kho: 'Kiểm tra tồn kho và ngưỡng Reorder của {name}'")
            
            if buy_to_trigger > 0:
                print(f"     2. Kích hoạt Restock: 'Đặt mua {buy_to_trigger + 1} cái {name}'")
                print(f"        (Giải thích: {stock} - {buy_to_trigger + 1} = {stock - (buy_to_trigger + 1)} (Thấp hơn ngưỡng {reorder}) -> 🔥 BÙM! Auto Restock)")
            else:
                print(f"     2. Kích hoạt Restock: 'Đặt mua 1 cái {name}' (Hiện tại đã thấp sẵn rồi)")
                
            print("-" * 60)

except Exception as e:
    print(f"❌ LỖI: {e}")